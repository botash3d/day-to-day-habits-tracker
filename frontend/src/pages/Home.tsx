import { Link } from "react-router-dom";
import { useAuth } from "../auth/authContext";
import { site } from "../config/site";
import "./Home.css";

const TASKS = [
  { text: "Review project notes", done: true },
  { text: "Gym session", done: true },
  { text: "Finish Python chapter 4", done: false },
  { text: "Plan tomorrow", done: false },
];
const LEARNING = [
  { name: "Python basics", pct: 72 },
  { name: "SQL fundamentals", pct: 45 },
  { name: "Spanish", pct: 30 },
];

function Navbar() {
  const { user, loading } = useAuth();
  return (
    <header className="nav">
      <div className="container nav-inner">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          {site.name}
        </Link>
        <nav className="nav-links" aria-label="Main">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <div className="nav-actions">
          {!loading &&
            (user ? (
              <>
                <Link className="btn btn-ghost" to="/dsa">
                  DSA
                </Link>
                <Link className="btn btn-ghost" to="/learn">
                  Learn
                </Link>
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled
                  title="Coming soon"
                >
                  Build <span className="btn-tag">Soon</span>
                </button>
                <Link className="btn btn-primary" to="/dashboard">
                  Dashboard
                </Link>
              </>
            ) : (
              <>
                <Link className="btn btn-ghost" to="/login">
                  Log in
                </Link>
                <Link className="btn btn-primary" to="/signup">
                  Sign up
                </Link>
              </>
            ))}
        </div>
      </div>
    </header>
  );
}

function Hero() {
  const { user } = useAuth();
  return (
    <section className="hero">
      <div className="hero-bg" aria-hidden="true" />
      <div className="container hero-inner">
        <span className="badge">{site.badge}</span>
        <h1>
          {site.headline.before}
          <span className="gradient-text">{site.headline.highlight}</span>
        </h1>
        <p className="lead">{site.description}</p>
        <div className="hero-actions">
          <Link
            className="btn btn-primary btn-lg"
            to={user ? "/dashboard" : "/signup"}
          >
            {user ? "Go to dashboard" : "Get started"}
          </Link>
          {user ? (
            <>
              <Link className="btn btn-ghost btn-lg" to="/dsa">
                Practice DSA
              </Link>
              <Link className="btn btn-ghost btn-lg" to="/learn">
                Learn
              </Link>
                <Link className="btn btn-ghost" to="/build">
                  Build
                </Link>
            </>
          ) : (
            <a className="btn btn-ghost btn-lg" href="#features">
              See features
            </a>
          )}
        </div>

        <div className="mock" aria-hidden="true">
          <div className="mock-bar">
            <i />
            <i />
            <i />
          </div>
          <div className="mock-body">
            <section className="panel">
              <h4>Today</h4>
              <ul className="task-list">
                {TASKS.map((t) => (
                  <li key={t.text} className={t.done ? "done" : ""}>
                    <span className="check">{t.done ? "✓" : ""}</span>
                    {t.text}
                  </li>
                ))}
              </ul>
            </section>
            <section className="panel">
              <h4>Learning</h4>
              {LEARNING.map((c) => (
                <div className="course" key={c.name}>
                  <div className="course-row">
                    <span>{c.name}</span>
                    <span>{c.pct}%</span>
                  </div>
                  <div className="bar">
                    <span style={{ width: `${c.pct}%` }} />
                  </div>
                </div>
              ))}
            </section>
          </div>
        </div>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section className="section" id="features">
      <div className="container">
        <div className="section-head">
          <h2>Why you will like it</h2>
          <p>Everything is designed to stay out of your way.</p>
        </div>
        <div className="grid-3">
          {site.features.map((f) => (
            <article className="feature" key={f.title}>
              <div className="feature-icon" aria-hidden="true">
                {f.icon}
              </div>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section className="section" id="how-it-works">
      <div className="container">
        <div className="section-head">
          <h2>How it works</h2>
          <p>Up and running in three steps.</p>
        </div>
        <div className="grid-3">
          {site.steps.map((s, i) => (
            <article className="feature" key={s.title}>
              <div className="step-num">{i + 1}</div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta() {
  const { user } = useAuth();
  return (
    <section className="section">
      <div className="container">
        <div className="cta">
          <h2>Ready to get started?</h2>
          <p>Create your account in under a minute.</p>
          <Link
            className="btn btn-primary btn-lg"
            to={user ? "/dashboard" : "/signup"}
          >
            {user ? "Go to dashboard" : "Create your account"}
          </Link>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <span>
          © {new Date().getFullYear()} {site.name}. All rights reserved.
        </span>
        <nav className="footer-links" aria-label="Footer">
          <Link to="/login">Log in</Link>
          <Link to="/signup">Sign up</Link>
        </nav>
      </div>
    </footer>
  );
}

export default function Home() {
  return (
    <div className="home">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}