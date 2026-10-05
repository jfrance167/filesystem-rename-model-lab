# Rename learning goals

Names bind to file identities; renaming to an alias of the same file is not ordinary source-name removal. Replacement displaces one destination binding, not every alias or an existing reference to its old object.

Atomic destination replacement is a namespace property; it does not establish durability, observer-free execution or a transaction over a sequence of renames. A failure report is not universally proof that no rename happened, especially with network filesystem retries.

The lab will teach complete admission, explicit unsupported context and independent expected snapshots. Those are conditional model guarantees, not a Python process sandbox or a kernel/filesystem audit.

Observed: Windows text IO converted LF help to CRLF; API/string-seam tests alone would miss it. Physical byte assertions found it. Writing fixed UTF8 bytes through native buffers preserved expectations; keeping the failed capture makes the correction reviewable. Matching numeric write counts are insufficient without exact int type: equal float/int-subclass results must still be rejected.
