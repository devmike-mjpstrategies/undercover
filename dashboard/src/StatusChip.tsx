import type { DecisionKind, Status } from "./api";
import { decisionLabels, statusLabels } from "./format";

export function StatusChip({ status }: Readonly<{ status: Status }>) {
  return <span className={`chip chip-${status}`}>{statusLabels[status]}</span>;
}

export function DecisionChip({
  decision,
}: Readonly<{ decision: DecisionKind }>) {
  return (
    <span className={`chip chip-${decision}`}>{decisionLabels[decision]}</span>
  );
}
