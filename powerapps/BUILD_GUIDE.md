# PowerApps Canvas App — Build Guide

PowerApps is a low-code tool, so this guide walks you through building the canvas app by hand in **make.powerapps.com**. It shares the same Dataverse `cr123_tasks` table that the React + FastAPI side uses.

## 1. Connect to Dataverse

1. Open https://make.powerapps.com → choose your environment (top right).
2. Click **+ Create** → **Blank canvas app** → name it `Task Tracker` → format **Tablet**.
3. In the left rail, click **Data** → **Add data** → search **Dataverse** → pick your `Tasks` table.

## 2. Screens

Create two screens (Insert → New screen):

| Screen | Purpose |
| --- | --- |
| `TaskListScreen` | Gallery of tasks with filter |
| `TaskEditScreen`  | Form for create/edit |

## 3. TaskListScreen controls

- **Header label**: text = `"Tasks"`, size 24, bold.
- **Search TextInput**: name it `txtSearch`.
- **Status Dropdown**: name `ddStatus`, Items = `["All","Not Started","In Progress","Done"]`.
- **+ New IconButton**: OnSelect:
  ```powerfx
  Set(selectedTask, Defaults(Tasks)); Navigate(TaskEditScreen, ScreenTransition.Cover)
  ```
- **Gallery `galTasks`**: Items =
  ```powerfx
  Sort(
    Filter(
      Tasks,
      (IsBlank(txtSearch.Text) || StartsWith(cr123_title, txtSearch.Text)) &&
      (ddStatus.Selected.Value = "All" || cr123_status = ddStatus.Selected.Value)
    ),
    cr123_duedate
  )
  ```
  - Title row: `ThisItem.cr123_title`
  - Subtitle: `ThisItem.cr123_priority & " · " & Text(ThisItem.cr123_duedate, "[$-en-US]mm/dd")`
  - OnSelect: `Set(selectedTask, ThisItem); Navigate(TaskEditScreen)`

## 4. TaskEditScreen controls

- **Form `frmTask`**: DataSource = `Tasks`, Item = `selectedTask`.
  - Fields: `cr123_title`, `cr123_description`, `cr123_status`, `cr123_priority`, `cr123_assigneeemail`, `cr123_duedate`.
- **Save Button**: OnSelect:
  ```powerfx
  SubmitForm(frmTask); If(frmTask.ErrorKind = ErrorKind.None, Navigate(TaskListScreen))
  ```
- **Delete Button** (visible only when editing): OnSelect:
  ```powerfx
  Remove(Tasks, selectedTask); Navigate(TaskListScreen)
  ```
- **Cancel Button**: `ResetForm(frmTask); Navigate(TaskListScreen)`.

## 5. (Optional) Call the FastAPI custom connector

If you want PowerApps to call your FastAPI endpoint instead of going directly to Dataverse (e.g. for cross-cutting business logic):

1. In **Power Apps** → **Custom connectors** → **+ New custom connector** → **Import from OpenAPI URL**.
2. Paste your FastAPI OpenAPI URL (e.g. `https://your-api.example.com/openapi.json`).
3. **Security** tab → Authentication = **OAuth 2.0** → Identity Provider = **Azure Active Directory**:
   - Client id = SPA app registration's client id
   - Client secret = (leave blank if confidential not needed)
   - Login URL = `https://login.microsoftonline.com`
   - Tenant ID = your tenant
   - Resource URL = `api://<API_CLIENT_ID>`
   - Scope = `api://<API_CLIENT_ID>/access_as_user`
4. Save → **Create connector**. Note the redirect URL it shows and add it to your **API app registration**'s redirect URIs.
5. In your app: **Data** → **Add data** → pick your custom connector → use it like any other source:
   ```powerfx
   ClearCollect(apiTasks, TaskTrackerAPI.GetTasks())
   ```

## 6. Publish

File → **Save** → **Publish**. Share the app with users (they need access to Dataverse + the custom connector).

## Notes on parity with React

| Concern | React/FastAPI | PowerApps |
| --- | --- | --- |
| Identity | Entra ID via MSAL.js → API JWT | Entra ID via the user's signed-in Power Apps session |
| Data | FastAPI → Dataverse Web API | Native Dataverse connector OR custom FastAPI connector |
| Business logic | FastAPI route handlers | Power Fx formulas, or the custom connector |
| Real-time sync | Polling/refresh | Refresh(Tasks) on screen visible |
