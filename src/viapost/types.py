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


class MessageContent(TypedDict, total=False):
    body_html: str
    body_plain: str
    content_status: Literal["available", "not_present", "unavailable"]
    raw_message_api_path: str


class MessageDetail(Message, MessageContent, total=False):
    content_variant: Literal["submitted"]


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


class InboundMessage(TypedDict, total=False):
    id: Required[str]
    domain_id: Required[str]
    from_address: Required[str]
    to_address: Required[str]
    attachment_count: Required[int]
    is_feedback_report: Required[bool]
    received_at: Required[str]
    subject: str


class InboundAttachment(TypedDict, total=False):
    filename: Required[str]
    content_type: Required[str]
    size_bytes: Required[int]
    download_url: str


class InboundMessageDetail(InboundMessage, total=False):
    attachments: Required[list[InboundAttachment]]
    content_status: Required[Literal["available", "not_present", "unavailable"]]
    content_variant: Required[Literal["received"]]
    body_html: str
    body_plain: str
    raw_message_api_path: str
    raw_message_url: str
    spf_result: Literal[
        "pass", "fail", "softfail", "neutral", "none", "temperror", "permerror", "not_evaluated"
    ]
    spf_aligned: bool | None
    dkim_result: Literal[
        "pass", "fail", "policy", "neutral", "none", "temperror", "permerror", "not_evaluated"
    ]
    dkim_aligned: bool | None
    dmarc_result: Literal[
        "pass", "fail", "quarantine", "reject", "none", "temperror", "permerror", "not_evaluated"
    ]
    dmarc_disposition: Literal["none", "quarantine", "reject"] | None
    authentication_evaluated_at: str | None


class InboundMessageList(TypedDict):
    messages: list[InboundMessage]


class InboundMessageListQuery(TypedDict, total=False):
    cursor: str
    limit: int
    domain_id: str
    search: str
    period: Literal["7d", "30d"]
    has_attachments: bool


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


WebhookEventType: TypeAlias = Literal[
    "queued",
    "sent",
    "delivered",
    "deferred",
    "soft_bounce",
    "hard_bounce",
    "complaint",
    "open",
    "click",
    "unsubscribe",
    "rejected",
    "failed",
    "inbound.received",
]
WebhookDeliveryEventType: TypeAlias = WebhookEventType | Literal["webhook.test"]
WebhookDeliveryStatus: TypeAlias = Literal["pending", "delivered", "failed"]


class WebhookEndpoint(TypedDict):
    id: str
    url: str
    event_types: list[WebhookEventType]
    enabled: bool
    max_attempts: int
    consecutive_failures: int
    disabled_at: str | None
    secret_rotated_at: str | None
    version: int
    created_at: str
    updated_at: str


class WebhookList(TypedDict):
    webhooks: list[WebhookEndpoint]


class CreateWebhookRequest(TypedDict):
    url: str
    event_types: list[WebhookEventType]


class CreateWebhookResponsePayload(TypedDict):
    endpoint: WebhookEndpoint
    secret: str


class UpdateWebhookRequest(TypedDict, total=False):
    expected_version: Required[int]
    enabled: bool
    event_types: list[WebhookEventType]
    max_attempts: int


class WebhookDeliverySummary(TypedDict):
    delivery_id: str
    event_type: WebhookDeliveryEventType
    status: WebhookDeliveryStatus
    attempt_count: int
    created_at: str
    updated_at: str
    next_retry_at: str | None
    delivered_at: str | None
    last_response_code: int | None
    last_duration_ms: int | None
    is_test: bool
    replay_of_delivery_id: str | None


class WebhookDeliveryPage(TypedDict, total=False):
    data: Required[list[WebhookDeliverySummary]]
    next_cursor: str


class WebhookDeliveryListQuery(TypedDict, total=False):
    cursor: str
    limit: int
    status: WebhookDeliveryStatus
    event_type: WebhookDeliveryEventType


class WebhookPayloadRedacted(TypedDict, total=False):
    event_type: WebhookDeliveryEventType
    message_id: str
    inbound_message_id: str
    occurred_at: str
    test: bool


class WebhookDeliveryAttempt(TypedDict):
    attempt: int
    status: str
    response_code: int | None
    duration_ms: int | None
    attempted_at: str
    next_retry_at: str | None


class WebhookDeliveryDetail(WebhookDeliverySummary):
    payload_redacted: WebhookPayloadRedacted
    attempts: list[WebhookDeliveryAttempt]


class WebhookOperationAccepted(TypedDict):
    delivery_id: str
    status: Literal["queued"]
    created_at: str


class WebhookReplayAccepted(WebhookOperationAccepted):
    source_delivery_id: str


class WebhookTestAccepted(WebhookOperationAccepted):
    is_test: Literal[True]


class RotateWebhookSecretResponsePayload(TypedDict, total=False):
    endpoint: Required[WebhookEndpoint]
    rotated_at: Required[str]
    secret: str


SuppressionReason: TypeAlias = Literal[
    "hard_bounce", "complaint", "unsubscribe", "manual", "invalid_address", "spam_trap"
]
SuppressionOrigin: TypeAlias = Literal["manual", "import", "automatic"]
SuppressionState: TypeAlias = Literal["active", "expired", "released"]


class Suppression(TypedDict, total=False):
    id: Required[str]
    email: Required[str]
    reason: Required[SuppressionReason]
    origin: Required[SuppressionOrigin]
    state: Required[SuppressionState]
    scope: Required[Literal["tenant"]]
    version: Required[int]
    created_at: Required[str]
    updated_at: Required[str]
    note: str | None
    domain_id: str | None
    source_message_id: str | None
    smtp_code: int | None
    expires_at: str | None
    released_at: str | None
    release_reason: str | None


class SuppressionList(TypedDict, total=False):
    data: Required[list[Suppression]]
    next_cursor: str


class SuppressionListQuery(TypedDict, total=False):
    cursor: str
    limit: int
    search: str
    reason: SuppressionReason
    state: Literal["active", "expired", "released", "all"]
    origin: SuppressionOrigin


class SuppressionDetailQuery(TypedDict, total=False):
    history_cursor: str
    history_limit: int


class SuppressionExportQuery(TypedDict, total=False):
    search: str
    reason: SuppressionReason
    state: Literal["active", "expired", "released", "all"]
    origin: SuppressionOrigin


class CreateSuppressionRequest(TypedDict, total=False):
    email: Required[str]
    reason: Required[Literal["manual", "invalid_address"]]
    expires_at: str | None
    note: str | None


class SuppressionHistoryEvent(TypedDict, total=False):
    id: Required[str]
    action: Required[Literal["created", "updated", "released", "reactivated"]]
    origin: Required[SuppressionOrigin]
    reason: Required[SuppressionReason]
    actor_type: Required[Literal["system", "user", "api_key"]]
    suppression_version: Required[int]
    occurred_at: Required[str]
    actor_id: str | None
    justification: str | None


class SuppressionDetail(TypedDict, total=False):
    suppression: Required[Suppression]
    history: Required[list[SuppressionHistoryEvent]]
    next_history_cursor: str


class ReleaseSuppressionRequest(TypedDict):
    expected_version: int
    acknowledge: Literal[True]
    justification: str


class SuppressionImportResult(TypedDict):
    total: int
    created: int
    reactivated: int
    skipped: int
    duplicates: int


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
