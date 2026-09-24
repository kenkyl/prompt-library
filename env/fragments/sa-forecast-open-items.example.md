<!-- EXAMPLE shape for OPEN_ITEMS (optional). Unresolved questions about your
     own CRM schema, permissions and integrations. Real one in
     private/fragments/sa-forecast-open-items.md -->
| Item | Status |
|---|---|
| Fields with no matching API name | Candidates listed in the field map. Confirm, or they live on another object. |
| Validation rules on stage / amount / close date | Not retrievable via the connector. Pull from the CRM admin UI before any write flow ships. |
| Triggers or flows enforcing stage gating | Invisible to metadata queries. Ask the CRM admin. |
| Definition of the vendor completeness field | Which fields it scores is undocumented. Worth asking. |
| Connector permissions still pending | Note which calls return an approval error and what they would unblock. |
