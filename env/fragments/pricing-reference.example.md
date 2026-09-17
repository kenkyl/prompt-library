<!-- EXAMPLE shape for the PRICING_REFERENCE variable.

     This variable is OPTIONAL. Leave it unset and section 4 disappears from
     the rendered prompt entirely.

     To use it, keep your real figures OUTSIDE this repo:
         private/fragments/pricing-reference.md
     and point at that file from private/env/<prompt-id>.env:
         PRICING_REFERENCE=@../fragments/pricing-reference.md

     Deliberately no digits and no currency symbols below. Placeholders are
     written <like-this> so the sanitization gate stays fully armed on this
     file -- if real figures ever land here by accident, the money patterns
     will block the commit instead of being suppressed by an allow rule.

     Include only what you actually want the assistant reasoning with. A short,
     current, accurate section beats a long stale one, and a wrong number here
     is worse than no number. -->

**Effective date:** <quarter>. Treat anything older than one quarter as stale and
say so rather than using it.

### List pricing and units

| SKU / edition | Unit | List | Notes |
|---|---|---|---|
| <product>, standard tier | per node per month | <amount> | annual commit; monthly is <pct> higher |
| <product>, premium tier | per node per month | <amount> | includes 24x7 and the higher SLA |
| <managed service> | per GB-month | <amount> | tiered, break at <volume> |
| <add-on module> | per cluster per year | <amount> | not sold standalone |

### Packaging and commit tiers

- Entry commit starts at <amount> annual; below that, self-serve only.
- Volume breaks at <amount> / <amount> / <amount> annual commit.
- Multi-year: <pct> for two years, <pct> for three, prepaid only.

### Professional services

- Preset engagement packages up to <amount>. Above that, scope with a services
  engagement manager before quoting anything.
- Blended day rate <amount>. Architecture review is a fixed-fee package.
- Training is priced per cohort, not per seat.

### Discount authority

| Discount | Approver |
|---|---|
| up to <pct> | account executive |
| up to <pct> | regional director |
| above <pct> | VP of sales and deal desk |

Never state discount authority, a floor price, or an approval threshold in
customer-facing material. Those are internal only.

### Marketplace and partner

- Cloud marketplace private offers carry a <pct> platform fee, so net price to us
  is below the same deal sold direct. Compare net, not list.
- Reseller margin is <pct> off list; distributor is <pct>.

### What to do when a figure is missing

Name the figure you need and where it would come from -- deal desk, the current
price book, the partner agreement. Do not interpolate between tiers, and do not
recall a number from training data.
