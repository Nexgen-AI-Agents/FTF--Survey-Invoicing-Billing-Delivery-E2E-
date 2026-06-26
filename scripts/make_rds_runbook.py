# -*- coding: utf-8 -*-
"""Generate a DevOps options doc: connect GitHub Actions to a PRIVATE RDS securely
(no public exposure)."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                HRFlowable, ListFlowable, ListItem)

OUT = r"C:\Users\Prateek Chandra\OneDrive - NexGen Enterprises\Claude\FTF_GitHubActions_to_PrivateRDS_SecureOptions.pdf"

styles = getSampleStyleSheet()
H1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=16.5, textColor=colors.HexColor('#1a3c5e'), spaceAfter=4)
SUB = ParagraphStyle('SUB', parent=styles['Normal'], fontSize=9.5, textColor=colors.HexColor('#555555'), spaceAfter=10)
H2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12.5, textColor=colors.HexColor('#1a3c5e'), spaceBefore=11, spaceAfter=5)
H3 = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=10.8, textColor=colors.HexColor('#23527c'), spaceBefore=7, spaceAfter=3)
BODY = ParagraphStyle('BODY', parent=styles['Normal'], fontSize=9.8, leading=14, spaceAfter=5)
CODE = ParagraphStyle('CODE', parent=styles['Code'], fontSize=8.3, leading=11.5, textColor=colors.HexColor('#0a0a0a'),
                      backColor=colors.HexColor('#f2f4f7'), borderPadding=6, leftIndent=4, rightIndent=4, spaceAfter=7)
FOOT = ParagraphStyle('foot', parent=BODY, fontSize=8.4, textColor=colors.HexColor('#666666'))


def code(t):
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
    return Paragraph(t, CODE)


def bullets(items):
    return ListFlowable([ListItem(Paragraph(t, BODY), leftIndent=12) for t in items],
                        bulletType='bullet', start='•', leftIndent=14)


doc = SimpleDocTemplate(OUT, pagesize=letter, topMargin=0.65 * inch, bottomMargin=0.65 * inch,
                        leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                        title="GitHub Actions to private RDS - secure options")
S = []
S.append(Paragraph("Connecting GitHub Actions to a Private RDS &mdash; Secure Options", H1))
S.append(Paragraph("FTF Survey Invoicing &amp; Billing Pipeline &nbsp;|&nbsp; DevOps options &nbsp;|&nbsp; Rev. 2026-06-25", SUB))
S.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=9))

S.append(Paragraph("Context", H2))
S.append(Paragraph("The RDS instance is private (reachable only from the web server) and must stay that way &mdash; agreed, "
    "public exposure is not acceptable. The invoice pipeline runs in GitHub Actions and needs to read the production MySQL "
    "for one step (order intake: which orders carry the &lsquo;needs-invoice&rsquo; flag). Below are four ways to give the "
    "pipeline private DB access <b>without</b> exposing RDS publicly. Any one of them is sufficient; pick whichever fits our "
    "infra best. The application/pipeline-side changes for each are listed so the split of work is clear.", BODY))

t = Table([
    ["DB instance", "production-ne-ftf-instance-1  (us-east-1, port 3306)"],
    ["Repo / workflow", "Nexgen-AI-Agents/FTF--Survey-Invoicing-Billing-Delivery-E2E-  /  invoice_pipeline.yml"],
    ["DB-dependent step", "A1 order intake (+ condo screening). All other steps already use HTTPS APIs."],
], colWidths=[1.4 * inch, 4.7 * inch])
t.setStyle(TableStyle([
    ('FONT', (0, 0), (-1, -1), 'Helvetica', 8.6),
    ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 8.6),
    ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3c5e')),
    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef2f6')),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cfd8e0')),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
]))
S.append(t)
S.append(Spacer(1, 6))

S.append(Paragraph("Option A &mdash; Self-hosted runner inside the VPC  (recommended, simplest)", H2))
S.append(Paragraph("Run the GitHub Actions job on a self-hosted runner placed in the same VPC/subnet, so it reaches RDS over "
    "the private network exactly like the web server does. RDS stays private; nothing is exposed to the internet.", BODY))
S.append(Paragraph("DevOps tasks:", H3))
S.append(bullets([
    "Launch a small instance (e.g. t3.small) in the private subnet, or reuse an existing in-VPC host / container.",
    "Add a security-group rule on RDS allowing <b>SG-to-SG</b> access on 3306 from the runner's security group "
    "(same pattern already used for the web server &mdash; no CIDR/public exposure).",
    "Install the GitHub Actions runner and register it to the repo (Settings &rarr; Actions &rarr; Runners), run it as a service. "
    "Outbound 443 to github.com is all it needs; no inbound ports.",
]))
S.append(Paragraph("Pipeline-side change (we handle):", H3))
S.append(bullets(["Set <font face='Courier'>runs-on: [self-hosted, linux]</font> on the DB-dependent workflow. No code change."]))

S.append(Paragraph("Option B &mdash; SSM Session Manager port-forwarding + GitHub OIDC  (no inbound ports, no static keys)", H2))
S.append(Paragraph("The GitHub job assumes an AWS IAM role via OIDC (short-lived, no stored credentials) and uses AWS Systems "
    "Manager to port-forward localhost:3306 to RDS <i>through</i> an in-VPC instance that runs the SSM agent (the web server "
    "qualifies). No security-group inbound rules, no public DB, fully auditable in CloudTrail.", BODY))
S.append(Paragraph("DevOps tasks:", H3))
S.append(bullets([
    "Ensure an in-VPC instance has the SSM agent + an instance profile (most AL2/Ubuntu AMIs do).",
    "Create an IAM role trusted by GitHub OIDC (provider <font face='Courier'>token.actions.githubusercontent.com</font>, "
    "scoped to this repo) granting <font face='Courier'>ssm:StartSession</font> on that instance + the port-forward document.",
    "Share the instance-id and role ARN with us.",
]))
S.append(Paragraph("Pipeline-side change (we handle):", H3))
S.append(code(
    "aws-actions/configure-aws-credentials@v4   # OIDC role assume\n"
    "aws ssm start-session --target i-XXXX \\\n"
    "  --document-name AWS-StartPortForwardingSessionToRemoteHost \\\n"
    "  --parameters host=\"<rds-endpoint>\",portNumber=3306,localPortNumber=3306 &\n"
    "# then MYSQL_HOST=127.0.0.1 for the pipeline step"))

S.append(Paragraph("Option C &mdash; Mesh VPN (Tailscale / WireGuard)", H2))
S.append(Paragraph("Place a subnet-router node in the VPC; the GitHub job joins the private mesh with an ephemeral auth key "
    "(official <font face='Courier'>tailscale/github-action</font>) and reaches RDS over the VPN. No public exposure, no inbound ports.", BODY))
S.append(bullets([
    "DevOps: run a Tailscale subnet router in the VPC advertising the RDS subnet; issue an ephemeral/tagged auth key.",
    "We handle: add the Tailscale step to the workflow before the DB step.",
]))

S.append(Paragraph("Option D &mdash; Run intake on the web server (which already reaches RDS)", H2))
S.append(Paragraph("Since the web server already has private DB access, run only the one DB-dependent step there on a schedule "
    "(cron/systemd timer); it records the flagged orders and the rest of the pipeline continues in GitHub Actions over HTTPS. "
    "Zero networking change &mdash; nothing new is exposed.", BODY))
S.append(bullets([
    "DevOps: allow a small scheduled job (Python) on the web server with read access to the order tables.",
    "We handle: package the intake step + a commit/push of results; everything else stays in CI.",
]))

S.append(Spacer(1, 8))
S.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=6))
S.append(Paragraph("Recommendation: <b>Option A</b> (self-hosted runner) is the least effort and keeps RDS fully private via an "
    "SG-to-SG rule. <b>Option B</b> (SSM + OIDC) is the most security-team-friendly &mdash; no inbound rules and no long-lived "
    "credentials. We&rsquo;ll implement the pipeline side for whichever you choose; only one option is needed.", FOOT))
S.append(Paragraph("Read access only is required (the intake step runs SELECT queries). No write access to the database is needed "
    "from CI.", FOOT))

doc.build(S)
print("WROTE:", OUT)
