import { api } from "./api";
import { useData } from "./useData";

export function Instructions() {
  const { data, error } = useData(api.instructions, null);
  if (error) {
    return (
      <p className="alert" role="alert">
        Could not load the instructions. {error}
      </p>
    );
  }
  if (!data) return <p className="muted">Loading the instructions</p>;
  return (
    <section className="panel" aria-labelledby="instructions-heading">
      <h2 id="instructions-heading">The agent&apos;s instructions</h2>
      <p className="muted">
        Read only. These are the instructions the agent gets.
      </p>
      <pre className="pre instructions">{data.text}</pre>
    </section>
  );
}
