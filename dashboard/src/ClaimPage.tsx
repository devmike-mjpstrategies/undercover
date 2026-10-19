import { useCallback } from "react";
import { api, type Claim } from "./api";
import { decisionLabels, label, money, when } from "./format";
import { SignOffPanel } from "./SignOffPanel";
import { StatusChip } from "./StatusChip";
import { Steps } from "./Steps";
import { useData } from "./useData";

export const CLAIM_REFRESH_MS = 2000;

function DecisionPanel({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  const { decision, payment } = claim;
  if (!decision) {
    return (
      <section className="panel">
        <h2>Decision</h2>
        <p className="muted">No decision yet.</p>
      </section>
    );
  }
  return (
    <>
      <section className="panel" aria-labelledby="decision-heading">
        <h2 id="decision-heading">Decision</h2>
        <p className="decision">
          <strong>{decisionLabels[decision.decision]}</strong>
          <span className="number">{money(decision.payout)}</span>
        </p>
        <p>{decision.reason}</p>
        <p className="muted">Policy wording: {decision.policy_section}</p>
        <p className="muted">Decided {when(decision.decided_at)}</p>
        {payment && (
          <p>
            Paid {money(payment.amount)} by {payment.released_by} on{" "}
            {when(payment.paid_at)}
          </p>
        )}
      </section>
      {claim.status === "awaiting_sign_off" && (
        <SignOffPanel
          claimId={claim.claim_id}
          payout={decision.payout}
          onSignedOff={onSignedOff}
        />
      )}
    </>
  );
}

function PolicyPanel({
  policyId,
  customerId,
}: Readonly<{ policyId: string; customerId: string }>) {
  const loadPolicy = useCallback(() => api.policy(policyId), [policyId]);
  const loadHistory = useCallback(() => api.history(customerId), [customerId]);
  const { data: policy } = useData(loadPolicy, null);
  const { data: history } = useData(loadHistory, null);
  if (!policy || !history) return null;
  return (
    <section className="panel" aria-labelledby="policy-heading">
      <h2 id="policy-heading">Policy</h2>
      <dl className="facts">
        <dt>Policy</dt>
        <dd className="mono">{policy.policy_id}</dd>
        <dt>Plan</dt>
        <dd>{policy.plan.name}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination}, {policy.trip.departs_on} to{" "}
          {policy.trip.returns_on}
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.map((a) => a.name).join(", ") || "None"}</dd>
      </dl>
      <h3>Earlier claims</h3>
      {history.length === 0 ? (
        <p className="muted">None</p>
      ) : (
        <ul className="plain">
          {history.map((earlier) => (
            <li key={earlier.claim_id}>
              <span className="mono">{earlier.filed_on}</span> {earlier.summary}
              , {earlier.outcome}
              {earlier.amount_paid > 0 && `, ${money(earlier.amount_paid)}`}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ClaimDetails({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <>
      <section className="panel">
        <h2>The customer&apos;s story</h2>
        <p>{claim.story}</p>
      </section>
      <section className="panel">
        <h2>Items claimed</h2>
        <div className="table-wrap">
          <table>
            <tbody>
              {claim.items.map((item) => (
                <tr key={item.description}>
                  <td>{item.description}</td>
                  <td>{label(item.category)}</td>
                  <td className="number">{money(item.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <h2>Documents</h2>
        {claim.documents.map((document) => (
          <article key={document.name} className="document">
            <h3>{document.name}</h3>
            <p className="muted">{label(document.type)}</p>
            <p>{document.content}</p>
          </article>
        ))}
      </section>
    </>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const load = useCallback(
    () => Promise.all([api.claim(claimId), api.steps(claimId)]),
    [claimId],
  );
  const { data, error, reload } = useData(load, CLAIM_REFRESH_MS);

  if (error && !data) {
    return (
      <p className="alert" role="alert">
        Could not load {claimId}. {error}
      </p>
    );
  }
  if (!data) return <p className="muted">Loading {claimId}</p>;
  const [claim, steps] = data;

  return (
    <>
      <section className="panel">
        <p className="title-line">
          <span className="mono">{claim.claim_id}</span>
          <StatusChip status={claim.status} />
        </p>
        <h1>{claim.summary}</h1>
        <p className="muted">
          {label(claim.claim_type)} in {claim.incident_location} on{" "}
          {claim.incident_date}, submitted {claim.submitted_on}. Claimed{" "}
          <span className="mono">{money(claim.amount_claimed)}</span>.
        </p>
      </section>
      <div className="columns">
        <div className="stack">
          <ClaimDetails claim={claim} />
        </div>
        <div className="stack">
          <DecisionPanel claim={claim} onSignedOff={reload} />
          <PolicyPanel
            policyId={claim.policy_id}
            customerId={claim.customer_id}
          />
        </div>
      </div>
      <section className="panel" aria-labelledby="steps-heading">
        <h2 id="steps-heading">What the agent did</h2>
        <Steps steps={steps} />
      </section>
    </>
  );
}
