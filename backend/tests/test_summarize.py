import pytest

from app.summary_agent import LONG_EMAIL_THRESHOLD_WORDS

# ── 10 realistic long emails (300+ words each) ────────────────────────────────
REAL_LONG_EMAILS = [
    pytest.param(
        """
Hi team,

Here is the weekly status update for MailMind Platform v2.0 as of this Friday. Overall project
status is YELLOW. We are three days behind schedule on the backend integration work due to
unexpected API rate limiting issues with the third-party email provider.

Completed this week: The authentication module has passed all unit and integration tests. Sarah
completed the redesigned inbox UI, approved by design. Database migration scripts for the new
schema have been written and peer-reviewed. Tom finished CI/CD pipeline improvements that reduce
deployment time by 40%.

In progress: Michael is 70% through the email parsing engine. He has completed core logic but
edge cases for malformed headers are taking longer than estimated — he expects to finish Thursday.
The notification system integration is 60% complete; Jennifer is on track for Tuesday.

Blockers: The API rate limiting issue is the primary blocker. We have been in contact with the
vendor support team since Monday and are waiting on a response regarding a higher tier. If we do
not hear back by Wednesday morning we will escalate to their enterprise team. There is also a
pending design review for notification templates that has been open five business days.

Risks: If the rate limiting issue is unresolved by Wednesday we may need to implement a local
caching layer, adding three to four days. I will present options at Thursday's leadership sync.

Action items: All pull requests must be submitted by next Friday at noon. All team members should
update Jira by end of day today. Engineering leads should attend the risk review call Thursday at
2 PM EST. The QA team needs the staging environment ready by Monday morning.

Please reach out if you have questions or concerns. Additionally, all engineers should plan
to attend the sprint retrospective on Friday afternoon before the weekend so we can carry
lessons learned into the next sprint planning session on Monday morning.

Best regards,
Marcus, Engineering Manager
        """,
        id="project-status-update",
    ),
    pytest.param(
        """
Dear Mr. Anderson,

I am writing to follow up on the ongoing platform performance issues your team has experienced
over the past three weeks. I want to personally assure you we take these concerns seriously and
are fully committed to resolution.

Summary of events: Your team first reported slow response times on October 3rd. Our support team
acknowledged the ticket the same day and attributed the issue to high server load. We deployed a
fix on October 7th and believed the issue resolved. However, you reported continued degradation
on October 10th and October 17th, which has significantly disrupted your team's daily operations.

Root cause: Our senior engineering team escalated this to Priority 1 on October 18th and identified
a memory leak in our email indexing service triggered specifically by accounts with more than 50,000
archived emails, which matches your account profile exactly. We deployed a hotfix to production on
October 20th and have monitored your account closely since. As of this morning, response times are
within our SLA commitment of under 200 milliseconds.

Remediation steps: We have added automated alerting for memory usage thresholds in the indexing
service. We are auditing all large enterprise accounts to identify others that may be affected. A
permanent architectural fix is scheduled for our November release.

Goodwill gesture: As acknowledgment of the disruption, I would like to offer three months of
service credit applied to your next invoice. Your account manager Priya Sharma will follow up with
the specific credit amount within two business days.

Going forward: I would like to schedule a monthly check-in call between my team and yours to
ensure any issues are caught early. Priya will send calendar invitations by Friday.

Thank you for your patience. Please do not hesitate to contact me directly with any concerns.

Sincerely,
David Kim, VP of Customer Success
        """,
        id="client-escalation",
    ),
    pytest.param(
        """
Hi Jennifer,

I am formally requesting approval for the Q4 2024 engineering team budget. The total requested
is $487,000. I want to walk through each category and its justification.

Personnel costs — $340,000: This covers salaries and benefits for our eight engineers and two QA
specialists for October, November, and December. It also includes contractor budget for two
additional engineers needed for the November product launch. I have screened three candidates
through our preferred staffing agency at a rate of $150 per hour for an estimated 400 hours total.

Infrastructure and tooling — $87,000: Cloud hosting is projected at $45,000 for Q4, a 15%
increase over Q3 due to anticipated traffic growth from the November launch. Enterprise license
renewals include GitHub Advanced Security at $8,200, Datadog monitoring at $12,400, and PagerDuty
at $6,800. The remaining $14,600 covers our CDN provider renewal due in November.

Training and development — $18,000: Four team members will attend AWS re:Invent in December,
which is critical preparation for our planned EKS migration in Q1. The remainder covers online
course subscriptions for the full team through our learning platform.

Software licenses — $42,000: This covers renewals of design tools, code signing certificates,
and our load testing platform. No new tools are being requested this quarter.

Expected ROI: This Q4 investment supports on-time delivery of the v2.0 product launch, which the
revenue team projects will generate $2.1 million in additional ARR within 12 months. The
contractor spend alone is recoverable within the first two months of incremental revenue.

Additionally, I want to flag a cost-saving opportunity on our Datadog contract. Our current
month-to-month rate is $12,400 per quarter. A two-year commitment would reduce this to $9,800 per
quarter, saving approximately $10,400 over the contract period. I am recommending we pursue this
negotiation as part of the Q4 renewal process, and I will need your approval to proceed.

I would appreciate approval by October 20th to begin contractor onboarding. Please let me know
if you need additional information or want to schedule a review call.

Thank you,
Marcus
        """,
        id="budget-approval-request",
    ),
    pytest.param(
        """
Hi Alex,

As we approach the end of Q3, it is time to begin preparation for the annual performance review
cycle. I am reaching out in advance to give you time to prepare and to outline the process.

The formal review period will run from November 4th through November 22nd. Self-assessments are
due November 8th. Manager assessments are due November 15th. Calibration sessions will be held
the week of November 18th. Final review meetings between managers and employees should be
completed by November 22nd. Any delays in submitting self-assessments or manager assessments will
compress the calibration timeline and should be escalated to HR immediately.

For this year's review cycle we are using an updated format that emphasizes impact over activity.
When completing your self-assessment, focus on three areas: outcomes you delivered and their
measurable business impact, how you demonstrated our core values in day-to-day work, and your
growth and development over the past year.

For impact, please provide specific examples with quantifiable results wherever possible. Instead
of "I improved the onboarding process," the ideal framing would be "I redesigned the onboarding
flow, which reduced time-to-first-value by 30% and increased 30-day retention by 12%."

Compensation: All merit increases are effective January 1st. The merit pool this year is 4.5% of
total base salaries, slightly higher than last year's 4.0% due to strong company performance.
Individual increases will range from 0% to 8% depending on rating and internal equity. Equity
refresh grants will be reviewed for employees at the senior level and above.

Please log into the HR portal by October 28th to confirm your role title, manager, and department
are current. If anything looks incorrect, contact HR directly before that date.

I look forward to recognizing the great work everyone has done this year. If you have questions
about the updated assessment format or the calibration process, please do not hesitate to reach
out and I am happy to schedule a brief call to walk through it together.

Best, Rachel, HR Business Partner
        """,
        id="hr-performance-review-prep",
    ),
    pytest.param(
        """
Hi all,

Below is the post-mortem summary for the production incident that occurred on October 14th
between 2:47 PM and 6:12 PM EST. The full report with detailed timeline, metrics, and root cause
analysis is available in Confluence under Incidents/2024/OCT-14.

Incident summary: Users experienced intermittent 503 errors and significant latency spikes across
all regions for 3 hours and 25 minutes. Approximately 12,000 user sessions were affected. Error
rate peaked at 23% at 3:15 PM. No data was lost or corrupted during the incident.

Root cause: The incident was triggered by a misconfigured autoscaling policy deployed as part of
the infrastructure update on October 13th. The policy had an incorrect minimum instance count of 1
instead of the required minimum of 5 for production traffic, combined with a scale-up threshold
that was too conservative. When traffic spiked at 2:47 PM as expected for a Monday afternoon, the
autoscaler could not provision new instances fast enough, causing existing instances to become
overwhelmed and return errors.

Contributing factor: The staging environment does not fully replicate production traffic patterns,
so the misconfiguration was not caught during pre-deployment testing. Additionally, our runbook
for infrastructure changes does not currently require explicit review of autoscaling policies as a
separate checklist item.

Detection: The incident was detected by Datadog monitoring at 2:51 PM, paging the on-call engineer
Tom Reyes within two minutes. Root cause was identified at 4:30 PM. The corrected policy was
deployed at 6:08 PM and full recovery confirmed at 6:12 PM.

Action items: Tom Reyes will update the infrastructure change runbook to require autoscaling policy
review by October 21st. Sarah Chen will configure load testing in staging to simulate Monday
afternoon traffic by October 28th. All autoscaling policies will be audited by November 1st.

Severity: P1. Total estimated revenue impact: $8,400.

Questions to the on-call rotation channel.
Platform Engineering Team
        """,
        id="production-incident-postmortem",
    ),
    pytest.param(
        """
Hi everyone,

With the MailMind v2.0 launch six weeks away, I want to share the official timeline and clarify
cross-team responsibilities to ensure we hit our November 15th target.

Launch overview: MailMind v2.0 is our most significant product release in two years. Key new
features include AI-powered email summarization, smart thread grouping, a redesigned mobile
experience, and enterprise SSO integration. This release directly supports our Q4 revenue goal of
$1.8 million in net new ARR and aligns with commitments made to three enterprise prospects in
late-stage contract negotiations.

Engineering milestones: Feature freeze is October 25th. No new features will be accepted after
this date. The release candidate build will be delivered to QA on October 28th. All critical and
high-priority bugs must be resolved by November 8th. Final build sign-off by engineering
leadership is due November 10th. Production deployment is scheduled for November 14th at 6 PM
EST with an estimated two-hour maintenance window.

QA milestones: Review of the release candidate begins October 28th. Regression testing must be
completed by November 5th. Performance and load testing is scheduled for November 6th and 7th.
All test results and sign-off documentation are due to engineering leadership by November 9th.

Marketing milestones: Launch announcement blog post and email campaign drafts must be finalized
by October 30th. Social media content calendar should be approved by November 1st. Press releases
go out November 12th under embargo. Customer in-app announcements launch simultaneously with the
product on November 15th. A launch webinar for current customers is scheduled for November 19th.

Customer success milestones: Updated help documentation and video tutorials must be published by
November 12th. Enterprise accounts must be briefed by November 13th. Dedicated launch support
rotation is required November 14th through November 18th.

Key risk: Enterprise SSO certification from our security audit partner is expected November 7th.
If this slips, SSO will be held and shipped as a point release within 30 days.

Please flag any blockers to me by October 22nd.

Sarah, Product Manager
        """,
        id="product-launch-timeline",
    ),
    pytest.param(
        """
Dear Ms. Thompson,

Thank you for sending the revised contract for our enterprise license renewal. Our legal and
procurement teams have reviewed the document and I am writing to outline the areas requiring
further negotiation before we can proceed to signature.

Pricing: The proposed annual increase of 18% significantly exceeds what was discussed during our
initial renewal conversations in August. Based on our usage data and current market rates for
comparable solutions, we believe an increase in the range of 6 to 8 percent is appropriate. Our
current contract value is $240,000 annually, so we are proposing renewal at $258,000 to $259,200.
We are prepared to commit to a three-year term at this rate rather than the current two-year
arrangement, which we hope demonstrates our long-term commitment to this partnership.

SLA commitments: Section 4.2 of the proposed contract reduces our guaranteed uptime SLA from
99.9% to 99.7%. This is not acceptable for our use case, as our product is built on top of your
infrastructure and any downtime directly affects our own customers. We require the SLA to remain
at 99.9% or above, with the current financial remedy structure of service credits at 10% of
monthly fees per 0.1% below threshold maintained.

Data portability: Section 8.4 currently states that we must submit a data export request 90 days
before contract termination to receive our data in a portable format. We require this reduced to
30 days and the format specified explicitly as JSON or CSV. This is a standard requirement we
have with all our data vendors.

Indemnification: Our legal team has flagged that Section 11 has been modified to limit your
indemnification obligations in the event of IP infringement claims. We require the indemnification
language restored to the version in our current contract.

We are eager to continue our partnership and believe these requested changes are reasonable. I
would like to schedule a call with you and your legal team for the week of October 21st to discuss
and reach agreement. Please let me know your availability.

Sincerely,
James O'Brien, VP of Procurement
        """,
        id="vendor-contract-negotiation",
    ),
    pytest.param(
        """
To: Board of Directors
Subject: Q3 Board Meeting Agenda — October 28th

Dear Board Members,

The next quarterly board meeting is scheduled for Monday, October 28th from 9 AM to 1 PM EST in
the Redwood Conference Room at our San Francisco headquarters. Video conference dial-in details are
included at the bottom of this email. All pre-read materials will be distributed via BoardVantage
by October 23rd. Please review them in advance of the meeting.

Agenda:

9:00–9:15 AM — Call to Order, Quorum Confirmation, and Approval of Q2 Meeting Minutes. Led by
Governance Committee Chair Linda Park.

9:15–10:00 AM — Q3 Financial Results and Q4 Outlook. Presented by CFO Robert Chen. Pre-read: Q3
Financial Package including income statement, balance sheet, cash flow statement, and budget
variance analysis.

10:00–10:45 AM — Product and Technology Update. Presented by the CTO and CPO. Pre-read: Product
Roadmap Update and Engineering Operations Report. This session includes a live demo of the
MailMind v2.0 release candidate scheduled for November 15th launch.

10:45–11:00 AM — Break.

11:00–11:30 AM — Sales and Revenue Update. Presented by CRO Lisa Nakamura. Pre-read: Q3 Sales
Report, Pipeline Analysis, and Customer Retention Summary.

11:30 AM–12:00 PM — People and Culture Report. Presented by CHRO Marcus Williams. Pre-read:
Headcount Report, Attrition Analysis, and Diversity and Inclusion Progress Report.

12:00–12:30 PM — Risk and Compliance Update. Presented by General Counsel Amanda Torres. Pre-read:
Risk Register, Compliance Status Summary, and Legal Matter Overview.

12:30–1:00 PM — Executive Session. Board members and CEO only.

Items requiring board approval: Approval of the 2025 annual operating budget. Approval of the
amendment to the equity incentive plan increasing the authorized share pool by 2.5 million shares.
Ratification of the appointment of KPMG as independent auditor for fiscal year 2025.

Please confirm attendance and dietary restrictions for the working lunch by October 21st.

Best regards,
Patricia Moore, Board Secretary
        """,
        id="board-meeting-agenda",
    ),
    pytest.param(
        """
To: All Employees
Subject: Updated Remote Work Policy Effective November 1st, 2024

Dear Team,

Following six months of gathering employee feedback and reviewing data on productivity,
collaboration, and satisfaction, we are pleased to announce an updated remote work policy
effective November 1st, 2024.

Core policy: All full-time employees are expected to work from the office a minimum of two days
per week — specifically Tuesday and Thursday, designated as core collaboration days. All other
days may be worked remotely at the employee's discretion, provided their role can be performed
effectively in a remote environment. Part-time employees should discuss their schedule with their
manager to determine appropriate in-office expectations.

Rationale: Our data shows that cross-functional collaboration, onboarding of new employees, and
in-person working sessions are the activities most significantly impacted by fully remote
arrangements. At the same time, focused individual and deep work is often performed as well or
better remotely. The two-day structure is designed to optimize for both.

Manager discretion: Team managers have the authority to require additional in-office days for
specific business reasons, including client meetings, team offsites, product launches, or critical
project phases. Managers requiring more than three in-office days per week must obtain approval
from their VP and HR Business Partner.

Equipment and stipends: All employees who do not yet have a complete home office setup will
receive a one-time stipend of $750 for equipment such as monitors, keyboards, or ergonomic
accessories. The monthly internet and phone stipend will increase from $50 to $75 per month
effective November 1st.

Commuter benefits: Pre-tax commuter benefit limits will be increased to the IRS maximum effective
January 1st, 2025. The benefits team will share full details separately.

Questions and feedback can be directed to people@company.com. We look forward to seeing more of
you on Tuesdays and Thursdays.

With appreciation,
Rachel Turner, Chief People Officer
        """,
        id="remote-work-policy",
    ),
    pytest.param(
        """
Dear Michael,

On behalf of MailMind Inc., I am delighted to formally extend an offer of employment for the
position of Senior Software Engineer, reporting to Marcus Rivera on the Platform Engineering team.
We were thoroughly impressed by your technical abilities and collaborative approach throughout the
interview process and are excited about the prospect of you joining us.

Position details: Your title will be Senior Software Engineer with a start date of November 18th,
2024. This is a full-time, exempt position. Your primary place of work will be our San Francisco
headquarters, with flexibility to work remotely two to three days per week in accordance with our
standard remote work policy.

Compensation: Your annual base salary will be $195,000, paid on a bi-weekly schedule. You will
be eligible for our annual performance bonus program with a target payout of 15% of base salary,
subject to company and individual performance. For 2024, you will receive a prorated bonus based
on your start date.

Equity: Subject to board approval, you will be granted an option to purchase 24,000 shares of
MailMind common stock at the fair market value on the date of grant. These options vest over four
years with a one-year cliff and monthly vesting thereafter, in accordance with our standard plan.

Benefits: You will be eligible for our full benefits package beginning on your first day. This
includes comprehensive medical, dental, and vision coverage for you and your dependents, with
premiums 90% paid by the company. You will receive 15 days of paid vacation in your first year,
increasing to 20 days after two years. We also offer 10 company holidays, paid sick leave, and
a 401(k) plan with a 4% company match that vests immediately.

Sign-on bonus: To assist with your transition, we are pleased to offer a one-time sign-on bonus
of $25,000, paid in your first paycheck. This is recoverable on a prorated basis if you leave
within 12 months of your start date.

Next steps: Please sign the attached offer letter and return it by October 22nd. If you have any
questions please contact me directly.

We look forward to having you join us.

Warm regards,
Jennifer Walsh, Head of Talent Acquisition
        """,
        id="job-offer-letter",
    ),
]


@pytest.mark.parametrize("email_body", REAL_LONG_EMAILS)
def test_real_email_detected_as_long(client, email_body):
    data = client.post("/api/v1/summarize", json={"text": email_body}).json()
    assert data["was_summarized"] is True
    assert data["word_count"] >= LONG_EMAIL_THRESHOLD_WORDS


@pytest.mark.parametrize("email_body", REAL_LONG_EMAILS)
def test_real_email_returns_valid_bullets(client, email_body):
    data = client.post("/api/v1/summarize", json={"text": email_body}).json()
    assert 3 <= len(data["bullets"]) <= 5
    assert all(isinstance(b, str) and b for b in data["bullets"])

# Exactly at the threshold
LONG_EMAIL = " ".join(["word"] * LONG_EMAIL_THRESHOLD_WORDS)

# One word short of threshold
SHORT_EMAIL = " ".join(["word"] * (LONG_EMAIL_THRESHOLD_WORDS - 1))

# Realistic short email
BRIEF_EMAIL = "Hi, just checking if you got my last message. Let me know. Thanks."


# ── Short email (below threshold) ─────────────────────────────────────────────

def test_short_email_returns_200(client):
    assert client.post("/api/v1/summarize", json={"text": SHORT_EMAIL}).status_code == 200


def test_short_email_not_summarized(client):
    data = client.post("/api/v1/summarize", json={"text": SHORT_EMAIL}).json()
    assert data["was_summarized"] is False
    assert data["bullets"] == []


def test_brief_email_not_summarized(client):
    data = client.post("/api/v1/summarize", json={"text": BRIEF_EMAIL}).json()
    assert data["was_summarized"] is False


def test_short_email_has_word_count(client):
    data = client.post("/api/v1/summarize", json={"text": SHORT_EMAIL}).json()
    assert data["word_count"] == LONG_EMAIL_THRESHOLD_WORDS - 1


# ── Long email (at or above threshold) ────────────────────────────────────────

def test_long_email_returns_200(client):
    assert client.post("/api/v1/summarize", json={"text": LONG_EMAIL}).status_code == 200


def test_long_email_is_summarized(client):
    data = client.post("/api/v1/summarize", json={"text": LONG_EMAIL}).json()
    assert data["was_summarized"] is True


def test_long_email_returns_bullets(client):
    data = client.post("/api/v1/summarize", json={"text": LONG_EMAIL}).json()
    assert 3 <= len(data["bullets"]) <= 5


def test_long_email_bullets_are_non_empty_strings(client):
    data = client.post("/api/v1/summarize", json={"text": LONG_EMAIL}).json()
    assert all(isinstance(b, str) and b for b in data["bullets"])


def test_long_email_word_count_correct(client):
    data = client.post("/api/v1/summarize", json={"text": LONG_EMAIL}).json()
    assert data["word_count"] == LONG_EMAIL_THRESHOLD_WORDS


# ── Threshold edge case ────────────────────────────────────────────────────────

def test_exactly_at_threshold_is_summarized(client):
    # 300 words → should summarize
    data = client.post("/api/v1/summarize", json={"text": LONG_EMAIL}).json()
    assert data["was_summarized"] is True


def test_one_below_threshold_is_not_summarized(client):
    data = client.post("/api/v1/summarize", json={"text": SHORT_EMAIL}).json()
    assert data["was_summarized"] is False


# ── Empty / missing input ──────────────────────────────────────────────────────

def test_empty_text_not_summarized(client):
    data = client.post("/api/v1/summarize", json={"text": ""}).json()
    assert data["was_summarized"] is False
    assert data["bullets"] == []
    assert data["word_count"] == 0


def test_missing_text_returns_422(client):
    assert client.post("/api/v1/summarize", json={}).status_code == 422


# ── Response shape ─────────────────────────────────────────────────────────────

def test_response_contains_all_fields(client):
    data = client.post("/api/v1/summarize", json={"text": LONG_EMAIL}).json()
    assert "bullets" in data
    assert "word_count" in data
    assert "was_summarized" in data


def test_word_count_is_integer(client):
    data = client.post("/api/v1/summarize", json={"text": LONG_EMAIL}).json()
    assert isinstance(data["word_count"], int)
