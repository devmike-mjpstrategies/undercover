import type { Step } from "./api";

const toolLabels: Record<string, string> = {
  get_claim: "Read the claim",
  get_policy: "Read the policy",
  get_claim_history: "Read the claim history",
  get_policy_wording: "Read the policy wording",
  record_decision: "Recorded the decision",
  pay_claim: "Paid the claim",
};

function split(text: string, separator: string): [string, string] {
  const at = text.indexOf(separator);
  return at === -1
    ? [text, ""]
    : [text.slice(0, at), text.slice(at + separator.length)];
}

function StepView({ step }: Readonly<{ step: Step }>) {
  if (step.kind === "message") return <p>{step.text}</p>;
  if (step.kind === "tool_call") {
    const [tool, args] = split(step.text, " ");
    return (
      <p>
        <strong>{toolLabels[tool] ?? tool}</strong>{" "}
        <span className="mono muted">{args}</span>
      </p>
    );
  }
  const [tool, result] = split(step.text, ": ");
  return (
    <details>
      <summary className="muted">Result of {tool}</summary>
      <pre className="pre">{result}</pre>
    </details>
  );
}

export function Steps({ steps }: Readonly<{ steps: Step[] }>) {
  if (steps.length === 0) {
    return <p className="muted">The agent has not worked on this claim yet.</p>;
  }
  return (
    <ol className="steps">
      {steps.map((step) => (
        <li key={step.id} className={`step step-${step.kind}`}>
          <StepView step={step} />
        </li>
      ))}
    </ol>
  );
}
