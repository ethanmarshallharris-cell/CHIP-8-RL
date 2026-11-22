import { useState } from "react";
import PlayTab from "./tabs/PlayTab.jsx";
import TrainTab from "./tabs/TrainTab.jsx";
import TestTab from "./tabs/TestTab.jsx";

const TABS = [
  { id: "train", label: "Train", component: TrainTab },
  { id: "test", label: "Test", component: TestTab },
  { id: "play", label: "Play", component: PlayTab },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("play");
  const Active = TABS.find((t) => t.id === activeTab).component;

  return (
    <div className="app">
      <header className="header">
        <h1>CHIP-8 RL</h1>
        <nav className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={tab.id === activeTab ? "tab active" : "tab"}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="content">
        <Active />
      </main>
    </div>
  );
}
