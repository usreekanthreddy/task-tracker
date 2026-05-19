import { IPublicClientApplication } from "@azure/msal-browser";
import { apiBaseUrl, apiRequest } from "./authConfig";

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  assignee_email?: string;
  due_date?: string;
  created_on?: string;
  modified_on?: string;
}

async function authHeader(instance: IPublicClientApplication): Promise<HeadersInit> {
  const account = instance.getActiveAccount() ?? instance.getAllAccounts()[0];
  if (!account) throw new Error("No signed-in account");
  const result = await instance.acquireTokenSilent({ ...apiRequest, account });
  return {
    Authorization: `Bearer ${result.accessToken}`,
    "Content-Type": "application/json",
  };
}

export async function listTasks(instance: IPublicClientApplication): Promise<Task[]> {
  const res = await fetch(`${apiBaseUrl}/api/tasks`, { headers: await authHeader(instance) });
  if (!res.ok) throw new Error(`List failed: ${res.status}`);
  return res.json();
}

export async function createTask(instance: IPublicClientApplication, payload: Partial<Task>): Promise<Task> {
  const res = await fetch(`${apiBaseUrl}/api/tasks`, {
    method: "POST",
    headers: await authHeader(instance),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Create failed: ${res.status}`);
  return res.json();
}

export async function updateTask(instance: IPublicClientApplication, id: string, payload: Partial<Task>): Promise<Task> {
  const res = await fetch(`${apiBaseUrl}/api/tasks/${id}`, {
    method: "PATCH",
    headers: await authHeader(instance),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Update failed: ${res.status}`);
  return res.json();
}

export async function deleteTask(instance: IPublicClientApplication, id: string): Promise<void> {
  const res = await fetch(`${apiBaseUrl}/api/tasks/${id}`, {
    method: "DELETE",
    headers: await authHeader(instance),
  });
  if (!res.ok && res.status !== 204) throw new Error(`Delete failed: ${res.status}`);
}
