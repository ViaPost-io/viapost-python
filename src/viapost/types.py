"""TypedDict models derived from the vendored OpenAPI contract."""

from typing import Any, Literal, TypeAlias

from typing_extensions import Required, TypedDict

JSONValue: TypeAlias = bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"] | None
JSONObject: TypeAlias = dict[str, Any]
QueryValue: TypeAlias = bool | int | float | str | list[bool | int | float | str] | None
Query: TypeAlias = dict[str, QueryValue]


class Attachment(TypedDict, total=False):
    filename: Required[str]
    content: Required[str]
    content_type: str


SendRequest = TypedDict(
    "SendRequest",
    {
        "from": Required[str],
        "to": Required[list[str]],
        "from_name": str,
        "reply_to": str,
        "cc": list[str],
        "bcc": list[str],
        "subject": str,
        "html": str,
        "text": str,
        "stream": Literal["transactional", "marketing"],
        "tags": list[str],
        "metadata": JSONObject,
        "template_id": str | None,
        "variables": JSONObject,
        "attachments": list[Attachment],
    },
    total=False,
)


class AcceptedMessage(TypedDict):
    message_id: str
    to: str


class RejectedMessage(TypedDict):
    to: str
    reason: Literal["invalid_address", "suppressed"]


class SendResult(TypedDict):
    accepted: list[AcceptedMessage]
    rejected: list[RejectedMessage]


class Message(TypedDict, total=False):
    id: Required[str]
    status: Required[str]
    stream: Required[Literal["transactional", "marketing"]]
    from_address: Required[str]
    to_address: Required[str]
    recipient_domain: Required[str]
    created_at: Required[str]
    subject: str | None
    api_key_id: str
    queued_at: str
    sent_at: str
    delivered_at: str
    failed_at: str
    first_opened_at: str
    first_clicked_at: str
    last_error: str | None


class MessageList(TypedDict):
    messages: list[Message]


class MessageEvent(TypedDict, total=False):
    type: Required[str]
    occurred_at: Required[str]
    recipient: str
    smtp_code: int
    enhanced_code: str
    diagnostic: str
    mx_host: str
    click_url: str


class MessageEventList(TypedDict):
    events: list[MessageEvent]


class EngagementResponse(TypedDict):
    since: str
    delivered: int
    opened: int
    clicked: int


class MessageTimeseriesDay(TypedDict):
    date: str
    queued: int
    processing: int
    sent: int
    delivered: int
    deferred: int
    bounced: int
    failed: int
    rejected: int
    complained: int


class TimeseriesResponse(TypedDict):
    since: str
    days: list[MessageTimeseriesDay]


class MetricsSummary(TypedDict):
    total: int
    delivered: int
    opened: int
    clicked: int
    bounced: int
    complained: int


class MetricsTimeseriesDay(TypedDict):
    date: str
    delivered: int
    open: int
    click: int
    soft_bounce: int
    hard_bounce: int
    complaint: int


class DomainMetrics(TypedDict):
    domain_id: str
    domain_name: str
    sent: int
    delivered: int
    opened: int
    clicked: int


class MetricsResponse(TypedDict):
    since: str
    until: str
    current: MetricsSummary
    previous: MetricsSummary
    timeseries: list[MetricsTimeseriesDay]
    by_domain: list[DomainMetrics]


class Domain(TypedDict):
    id: str
    name: str
    status: Literal["pending", "verified", "failed", "disabled"]
    spf_verified: bool
    dkim_verified: bool
    dmarc_verified: bool
    return_path_subdomain: str
    created_at: str


class DomainList(TypedDict):
    domains: list[Domain]


class CreateDomainRequest(TypedDict):
    name: str


class DNSRecord(TypedDict):
    type: str
    name: str
    value: str
    purpose: Literal["dkim", "spf", "dmarc"]


class DNSRecordList(TypedDict):
    dns_records: list[DNSRecord]


class CreateDomainResponse(TypedDict):
    domain: Domain
    dns_records: list[DNSRecord]


class RotateDKIMResponse(TypedDict):
    selector: str
    public_key: str
    status: str


class TemplateVariable(TypedDict, total=False):
    name: Required[str]
    var_type: Required[Literal["string", "number"]]
    fallback_value: str | None


class EmailTemplate(TypedDict, total=False):
    id: Required[str]
    name: Required[str]
    created_at: Required[str]
    updated_at: Required[str]
    current_draft_version_id: str
    published_version_id: str


class EmailTemplateVersion(TypedDict, total=False):
    id: Required[str]
    version_number: Required[int]
    status: Required[Literal["draft", "published", "superseded"]]
    content_json: Required[JSONObject]
    variables: Required[list[TemplateVariable]]
    created_at: Required[str]
    updated_at: Required[str]
    subject: str
    compiled_html: str
    compiled_text: str
    published_at: str


class TemplateList(TypedDict):
    templates: list[EmailTemplate]


class CreateTemplateRequest(TypedDict):
    name: str


class CreateTemplateResponse(TypedDict):
    template: EmailTemplate
    draft: EmailTemplateVersion


class TemplatePreconditionRequest(TypedDict, total=False):
    expected_version_id: str
    expected_updated_at: str


class UpdateTemplateDraftRequest(TypedDict, total=False):
    content_json: Required[JSONObject]
    variables: Required[list[TemplateVariable]]
    subject: str | None
    expected_version_id: str
    expected_updated_at: str


class UpdateTemplateDraftResponse(TypedDict):
    draft: EmailTemplateVersion
    preview_html: str
    preview_text: str


class PreviewTemplateRequest(TypedDict, total=False):
    variables: JSONObject


class PreviewTemplateResponse(TypedDict):
    subject: str
    html: str
    text: str


class TemplateVersionList(TypedDict):
    versions: list[EmailTemplateVersion]


class CreateTemplateAssetRequest(TypedDict):
    filename: str
    content_type: str


class TemplateAssetPolicy(TypedDict):
    upload_url: str
    upload_fields: dict[str, str]
    asset_url: str


class WebhookEndpoint(TypedDict):
    id: str
    url: str
    event_types: list[str]
    enabled: bool
    max_attempts: int
    created_at: str


class WebhookList(TypedDict):
    webhooks: list[WebhookEndpoint]


class CreateWebhookRequest(TypedDict):
    url: str
    event_types: list[str]


class CreateWebhookResponse(TypedDict):
    endpoint: WebhookEndpoint
    secret: str


class Automation(TypedDict, total=False):
    id: Required[str]
    name: Required[str]
    status: Required[Literal["disabled", "enabled", "archived"]]
    graph: Required[JSONObject]
    created_at: Required[str]
    updated_at: Required[str]
    current_version_id: str | None


class AutomationList(TypedDict):
    data: list[Automation]


class CreateAutomationRequest(TypedDict):
    name: str


class RenameAutomationRequest(TypedDict):
    name: str


class UpdateAutomationDraftRequest(TypedDict, total=False):
    graph: Required[JSONObject]
    name: str


class AutomationRun(TypedDict, total=False):
    id: Required[str]
    automation_id: Required[str]
    automation_version_id: Required[str]
    contact_id: Required[str]
    trigger_event_id: Required[str]
    status: Required[Literal["running", "completed", "failed", "cancelled"]]
    graph_snapshot: Required[JSONObject]
    started_at: Required[str]
    created_at: Required[str]
    updated_at: Required[str]
    completed_at: str | None
    error: str | None


class AutomationRunStep(TypedDict, total=False):
    id: Required[str]
    step_key: Required[str]
    step_type: Required[str]
    status: Required[str]
    attempts: Required[int]
    created_at: Required[str]
    updated_at: Required[str]
    branch: str
    error: str | None
    scheduled_at: str | None
    started_at: str | None
    completed_at: str | None


class AutomationRunList(TypedDict, total=False):
    data: Required[list[AutomationRun]]
    next_cursor: str


class AutomationRunDetail(TypedDict):
    run: AutomationRun
    steps: list[AutomationRunStep]


class UsagePeriod(TypedDict):
    start: str
    end: str
    timezone: Literal["UTC"]


class MonthlyUsage(TypedDict):
    period: UsagePeriod
    used: int
    limit: int | None
    remaining: int | None
    unlimited: bool
