<!-- EXAMPLE shape for LINK_TEMPLATE. Substitute your own CRM org host; yours
     identifies your instance, so keep it in
     private/fragments/sa-forecast-link-template.md -->
Every record reference is a link. Build them from IDs already returned by the
queries.

| Target | Pattern |
|---|---|
| Opportunity | `https://<your-org>.example.com/r/Opportunity/{Id}/view` |
| Account | `https://<your-org>.example.com/r/Account/{AccountId}/view` |
| Task / activity | `https://<your-org>.example.com/r/Task/{Id}/view` |
| Call recording | Use the call URL returned by search verbatim |
| Calendar event | The event's own html link field |
| Mail thread | The thread permalink from the mail tool |
| Document | The web view link from the drive tool |
| Issue | The issue URL from the issue tracker |

Never construct a link from a guessed ID. If a tool did not return a URL, render
plain text and say where the evidence came from.
