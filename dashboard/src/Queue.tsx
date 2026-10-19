import { api } from "./api";
import { day, label, money, statuses } from "./format";
import { DecisionChip, StatusChip } from "./StatusChip";
import { useData } from "./useData";

export const QUEUE_REFRESH_MS = 5000;

export function Queue() {
  const { data: claims, error } = useData(api.claims, QUEUE_REFRESH_MS);

  if (error) {
    return (
      <p className="alert" role="alert">
        Could not load the queue. {error}
      </p>
    );
  }
  if (!claims) return <p className="muted">Loading the queue</p>;

  return (
    <>
      <section className="counts" aria-label="Claims by status">
        {statuses.map((status) => (
          <div className="panel count" key={status}>
            <StatusChip status={status} />
            <strong data-testid={`count-${status}`}>
              {claims.filter((claim) => claim.status === status).length}
            </strong>
          </div>
        ))}
      </section>
      <section className="panel">
        <h2>Claims queue</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Claim</th>
                <th>Customer</th>
                <th>Type</th>
                <th className="wide">Summary</th>
                <th className="number">Claimed</th>
                <th>Submitted</th>
                <th>Status</th>
                <th>Decision</th>
                <th className="number">Payout</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.claim_id}>
                  <td className="mono">
                    <a href={`#/claims/${claim.claim_id}`}>{claim.claim_id}</a>
                  </td>
                  <td>{claim.customer_name}</td>
                  <td>{label(claim.claim_type)}</td>
                  <td className="wide">{claim.summary}</td>
                  <td className="number">{money(claim.amount_claimed)}</td>
                  <td className="mono">{day(claim.submitted_on)}</td>
                  <td>
                    <StatusChip status={claim.status} />
                  </td>
                  <td>
                    {claim.decision && (
                      <DecisionChip decision={claim.decision} />
                    )}
                  </td>
                  <td className="number">
                    {claim.payout === null ? "" : money(claim.payout)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
