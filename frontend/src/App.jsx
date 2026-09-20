import { useState } from "react";
import Sidebar from "./components/Sidebar";
import RepoInput from "./components/RepoInput";
import Overview from "./components/Overview";
import Chat from "./components/Chat";
import History from "./components/History";
import Onboarding from "./components/Onboarding";
import Evaluation from "./components/Evaluation";

/**
 * Layout: a fixed sidebar (nav + branding) beside a scrollable main
 * content area. `repo` holds the currently indexed repo; Overview/Chat/
 * History/Onboarding/Evaluation are disabled in the sidebar until it's
 * set. "Index Repo" always holds the indexing form (own dedicated tab,
 * not a settings/config concern), so indexing a different repo later is
 * just "go back to Index Repo and paste a new URL."
 */
export default function App() {
  const [repo, setRepo] = useState(null);
  const [activeTab, setActiveTab] = useState("index");

  function handleIndexed(repoInfo) {
    setRepo(repoInfo);
    setActiveTab("overview");
  }

  return (
    <div className="app-layout">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} repo={repo} />

      <main className="main-content">
        <div className="content-inner">
          {/* Keyed by activeTab so switching sidebar tabs remounts this
              wrapper and replays the fade-in — a subtle transition
              instead of an instant content swap. */}
          <div key={activeTab} className="tab-fade">
            {activeTab === "index" && <RepoInput onIndexed={handleIndexed} />}

            {activeTab === "overview" && repo && (
              <Overview key={repo.repoId} repoId={repo.repoId} repoName={repo.repoName} />
            )}

            {activeTab === "chat" && repo && (
              <Chat key={repo.repoId} repoId={repo.repoId} repoName={repo.repoName} />
            )}

            {activeTab === "history" && repo && (
              <History key={repo.repoId} repoId={repo.repoId} repoName={repo.repoName} />
            )}

            {activeTab === "onboarding" && repo && (
              <Onboarding key={repo.repoId} repoId={repo.repoId} repoName={repo.repoName} />
            )}

            {activeTab === "evaluation" && repo && (
              <Evaluation key={repo.repoId} repoId={repo.repoId} repoName={repo.repoName} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
