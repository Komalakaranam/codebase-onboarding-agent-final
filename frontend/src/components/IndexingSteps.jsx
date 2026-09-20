import { CheckIcon, ErrorIcon } from "./StatusIcons";

/**
 * The backend does clone → parse → embed → store as one synchronous
 * call (no job queue / progress-polling infra exists yet), so this
 * checklist is a hybrid: "clone" and "parse" advance on a timer while
 * the request is in flight (representative of typical repo sizes),
 * "embed" stays active until the real response lands (it's the step
 * that actually dominates total time and varies most by repo size),
 * and the terminal state (all done, or whichever step actually failed)
 * comes from the real HTTP response — see RepoInput's classifyErrorStep.
 */
export default function IndexingSteps({ steps, statuses }) {
  return (
    <ul className="step-list">
      {steps.map(({ id, label }) => {
        const state = statuses[id];
        return (
          <li key={id} className={"step-item step-" + state}>
            <span className="step-icon">
              {state === "done" && <CheckIcon />}
              {state === "error" && <ErrorIcon />}
              {state === "active" && <span className="spinner" />}
              {state === "pending" && <span className="step-dot" />}
            </span>
            <span>{label}</span>
          </li>
        );
      })}
    </ul>
  );
}
