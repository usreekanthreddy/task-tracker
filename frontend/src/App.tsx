import { useEffect, useState } from "react";
import {
  AuthenticatedTemplate,
  UnauthenticatedTemplate,
  useMsal,
} from "@azure/msal-react";
import { apiRequest } from "./authConfig";
import { listTasks, createTask, updateTask, deleteTask, Task } from "./api";

export default function App() {
  const { instance, accounts } = useMsal();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ title: "", priority: "Medium", status: "Not Started" });

  useEffect(() => {
    if (accounts[0]) instance.setActiveAccount(accounts[0]);
  }, [accounts, instance]);

  async function refresh() {
    try {
      setTasks(await listTasks(instance));
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.title.trim()) return;
    await createTask(instance, draft);
    setDraft({ title: "", priority: "Medium", status: "Not Started" });
    await refresh();
  }

  async function onStatusChange(t: Task, status: string) {
    await updateTask(instance, t.id, { status });
    await refresh();
  }

  async function onDelete(t: Task) {
    await deleteTask(instance, t.id);
    await refresh();
  }

  return (
    <div className="container">
      <header>
        <h1>Task Tracker</h1>
        <UnauthenticatedTemplate>
          <button onClick={() => instance.loginRedirect(apiRequest)}>Sign in with Microsoft</button>
        </UnauthenticatedTemplate>
        <AuthenticatedTemplate>
          <div className="user">
            <span>{accounts[0]?.username}</span>
            <button onClick={() => instance.logoutRedirect()}>Sign out</button>
          </div>
        </AuthenticatedTemplate>
      </header>

      <AuthenticatedTemplate>
        <button onClick={refresh}>Load tasks</button>
        {error && <p className="error">Error: {error}</p>}

        <form onSubmit={onCreate} className="new-task">
          <input
            placeholder="New task title"
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
          />
          <select value={draft.priority} onChange={(e) => setDraft({ ...draft, priority: e.target.value })}>
            <option>Low</option><option>Medium</option><option>High</option>
          </select>
          <button type="submit">Add</button>
        </form>

        <ul className="task-list">
          {tasks.map((t) => (
            <li key={t.id} className={`task status-${t.status.replace(/\s+/g, "-").toLowerCase()}`}>
              <div>
                <strong>{t.title}</strong>
                <small> · {t.priority}</small>
              </div>
              <div className="actions">
                <select value={t.status} onChange={(e) => onStatusChange(t, e.target.value)}>
                  <option>Not Started</option><option>In Progress</option><option>Done</option>
                </select>
                <button onClick={() => onDelete(t)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      </AuthenticatedTemplate>
    </div>
  );
}
