<!-- EXAMPLE shape for SCOPE_FILTERS: the CRM clauses that scope the book.
     Yours name your team and territory, so they are internal schema. Keep the
     real ones in private/fragments/sa-forecast-scope-filters.md

     Note the last row. Scoping by record owner is the classic mistake here:
     opportunities carry a seller as owner with a separate architect assigned,
     so owner-scoping silently drops most of the book. -->
| SA filter | `<architect relationship>.Name IN ('<name>','<name>')` |
| Territory filter | `<territory field> = '<territory>'` — required. Opportunities assigned to these architects but stamped to another territory are out of scope. |
| Other validation stamps | `<region field> = '<region>'`, `<role field> = '<role>'` |
| Never scope by | the record owner — opportunities carry a seller as owner with a separate architect |
