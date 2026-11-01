import { useState } from "react";
import type { ExerciseStep } from "../api/client";
import CodeBox from "./CodeBox";
import LessonMarkdown from "./LessonMarkdown";

export default function ExerciseSteps({ steps }: { steps: ExerciseStep[] }) {
  const [checked, setChecked] = useState<boolean[]>(() => steps.map(() => false));
  const done = checked.filter(Boolean).length;

  function toggle(index: number) {
    setChecked((prev) => prev.map((value, i) => (i === index ? !value : value)));
  }

  return (
    <section className="learn-exercise" aria-labelledby="try-it-heading">
      <div className="learn-exercise-head">
        <h2 id="try-it-heading">Try it</h2>
        <span className="muted">
          {done} of {steps.length} steps checked
        </span>
      </div>
      <p className="muted">
        Run these steps on your own computer. Tick a step once what you see
        matches.
      </p>

      <ol className="learn-steps">
        {steps.map((step, index) => (
          <li
            key={index}
            className={`learn-step${checked[index] ? " is-done" : ""}`}
          >
            <div className="learn-step-num">{index + 1}</div>
            <div className="learn-step-body">
              <LessonMarkdown>{step.instruction}</LessonMarkdown>

              {step.command && (
                <CodeBox label="Command" text={step.command}>
                  {step.command}
                </CodeBox>
              )}

              {step.expected_output && (
                <div className="learn-output">
                  <div className="learn-code-bar">
                    <span>Expected output</span>
                  </div>
                  <pre>{step.expected_output}</pre>
                </div>
              )}

              <label className="learn-check">
                <input
                  type="checkbox"
                  checked={checked[index]}
                  onChange={() => toggle(index)}
                />
                <span>{step.check || "I completed this step"}</span>
              </label>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}