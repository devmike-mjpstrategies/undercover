import { useState, type SubmitEvent } from "react";
import { api } from "./api";
import { money } from "./format";
import { useData } from "./useData";

interface Props {
  claimId: string;
  payout: number;
  onSignedOff: () => void;
}

export function SignOffPanel({
  claimId,
  payout,
  onSignedOff,
}: Readonly<Props>) {
  const { data: handlers } = useData(api.handlers, null);
  const [handlerId, setHandlerId] = useState("");
  const [error, setError] = useState<string>();
  const able = (handlers ?? []).filter((h) => h.can_approve_over_limit);

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    api.signOff(claimId, handlerId).then(onSignedOff, (reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Failed");
    });
  };

  return (
    <section className="panel sign-off" aria-labelledby="sign-off-heading">
      <h2 id="sign-off-heading">Sign-off</h2>
      <p>
        The payout of {money(payout)} needs a handler&apos;s sign-off before it
        is paid.
      </p>
      <form onSubmit={submit} className="form">
        <label>
          Handler
          <select
            value={handlerId}
            onChange={(event) => {
              setHandlerId(event.target.value);
            }}
          >
            <option value="">Choose a handler</option>
            {able.map((handler) => (
              <option key={handler.handler_id} value={handler.handler_id}>
                {handler.name}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={handlerId === ""}>
          Sign off and pay
        </button>
      </form>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
