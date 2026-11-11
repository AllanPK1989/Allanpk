import { useEffect, useMemo, useState } from "react";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, ChipSelect, Confirm, Empty, Field, Modal, Notice, PageHeader, Search } from "../components/ui";
import { hashPassword, validateEmployeeId, validatePassword } from "../lib/auth";
import { formatDateTime } from "../lib/dates";
import { newId, nowIso } from "../lib/ids";
import { can, canAny, canManageUserRole } from "../lib/permissions";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import { ROLE_LABELS, ROLES, type Role, type User } from "../types";

const ROLE_ORDER: Record<Role, number> = { owner: 0, maintenance_supervisor: 1, production_supervisor: 2, technician: 3 };

function tempPassword(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789";
  const bytes = new Uint8Array(10);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
}

export function Users() {
  const { snapshot, mutate, linesById } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const [q, setQ] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [editing, setEditing] = useState<User | "new" | null>(null);
  const [resetFor, setResetFor] = useState<User | null>(null);
  const [toggle, setToggle] = useState<User | null>(null);

  const allowed = canAny(user, "user.manage_technicians", "user.manage_all");
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return snapshot.users
      .filter((u) => (showInactive || u.active) && (!needle || `${u.employeeId} ${u.name} ${u.phone} ${u.email}`.toLowerCase().includes(needle)))
      .sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role] || a.name.localeCompare(b.name));
  }, [snapshot.users, q, showInactive]);

  if (!allowed) {
    return (
      <Notice tone="warning" icon="lock">
        Your role does not manage users.
      </Notice>
    );
  }

  const activeOwners = snapshot.users.filter((u) => u.active && u.role === "owner").length;

  const toggleActive = (target: User) => {
    if (target.id === user.id) return toast.error("You cannot deactivate your own account");
    if (target.active && target.role === "owner" && activeOwners <= 1) return toast.error("Keep at least one active owner");
    mutate(
      (d) => {
        const u = d.users.find((x) => x.id === target.id);
        if (!u) return;
        u.active = !u.active;
        u.updatedAt = nowIso();
      },
      { entity: "user", entityId: target.id, action: target.active ? "deactivate" : "activate", summary: `${target.employeeId} ${target.active ? "deactivated" : "activated"} by ${user.name}` },
    );
    toast.success(target.active ? "User deactivated" : "User activated");
  };

  return (
    <div>
      <PageHeader
        title="Users"
        subtitle={`${snapshot.users.filter((u) => u.active).length} active accounts`}
        actions={
          <Button variant="primary" icon="plus" onClick={() => setEditing("new")}>
            New user
          </Button>
        }
      />
      {!can(user, "user.manage_all") && (
        <div className="mb-8" style={{ marginBottom: 12 }}>
          <Notice tone="accent" icon="info">
            As maintenance supervisor you manage technician accounts. The owner manages supervisors and owners.
          </Notice>
        </div>
      )}
      <div className="filters">
        <Search value={q} onChange={setQ} placeholder="Search ID, name, phone" />
        <label className="check small">
          <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} /> Show inactive
        </label>
      </div>
      <Card tight>
        {rows.length === 0 ? (
          <Empty icon="users" title="No users match" />
        ) : (
          <div className="table-wrap">
            <table className="data responsive">
              <thead>
                <tr>
                  <th>Employee ID</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Lines</th>
                  <th>Contact</th>
                  <th>Last login</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((u) => {
                  const manageable = canManageUserRole(user, u.role);
                  const locked = u.lockedUntil && new Date(u.lockedUntil).getTime() > Date.now();
                  return (
                    <tr key={u.id}>
                      <td data-label="Employee ID" className="primary-cell">{u.employeeId}</td>
                      <td data-label="Name">
                        {u.name}
                        {u.skills && <div className="sub-cell">{u.skills}</div>}
                      </td>
                      <td data-label="Role">{ROLE_LABELS[u.role]}</td>
                      <td data-label="Lines">{u.role === "production_supervisor" ? (u.lineIds.length ? u.lineIds.map((id) => linesById.get(id)?.code).filter(Boolean).join(", ") : "All lines") : "—"}</td>
                      <td data-label="Contact">
                        {u.phone || u.email ? (
                          <>
                            {u.phone && <div>{u.phone}</div>}
                            {u.email && <div className="sub-cell">{u.email}</div>}
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td data-label="Last login" className="nowrap">{formatDateTime(u.lastLoginAt)}</td>
                      <td data-label="Status">
                        {!u.active ? <Badge>Inactive</Badge> : locked ? <Badge tone="critical">Locked</Badge> : u.mustChangePassword ? <Badge tone="warning">Temp password</Badge> : <Badge tone="good">Active</Badge>}
                      </td>
                      <td data-label="" className="right nowrap">
                        {manageable && (
                          <>
                            <Button size="sm" variant="ghost" icon="edit" aria-label="Edit" onClick={() => setEditing(u)} />
                            <Button size="sm" variant="ghost" icon="lock" aria-label="Reset password" title="Reset password" onClick={() => setResetFor(u)} />
                            {u.id !== user.id && (
                              <Button size="sm" variant="ghost" onClick={() => setToggle(u)}>
                                {u.active ? "Deactivate" : "Activate"}
                              </Button>
                            )}
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <UserForm open={editing !== null} user={editing === "new" ? undefined : (editing ?? undefined)} onClose={() => setEditing(null)} />
      <ResetPassword user={resetFor} onClose={() => setResetFor(null)} />
      <Confirm open={toggle !== null} onClose={() => setToggle(null)} title={toggle?.active ? `Deactivate ${toggle?.name}?` : `Activate ${toggle?.name}?`} text={toggle?.active ? "They can no longer sign in. Their history stays on every work order." : "They can sign in again."} confirmLabel={toggle?.active ? "Deactivate" : "Activate"} danger={Boolean(toggle?.active)} onConfirm={() => toggle && toggleActive(toggle)} />
    </div>
  );
}

function UserForm({ open, user: target, onClose }: { open: boolean; user?: User; onClose: () => void }) {
  const { snapshot, mutate } = useStore();
  const actor = useCurrentUser();
  const toast = useToast();
  const manageAll = can(actor, "user.manage_all");
  const roles = ROLES.filter((r) => canManageUserRole(actor, r));
  const blank = () => ({ employeeId: "", name: "", role: (manageAll ? "technician" : "technician") as Role, lineIds: [] as string[], phone: "", email: "", skills: "", password: tempPassword(), active: true });
  const [f, setF] = useState(blank);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ employeeId: string; password: string } | null>(null);

  useEffect(() => {
    if (!open) return;
    setCreated(null);
    setError(null);
    if (target) setF({ employeeId: target.employeeId, name: target.name, role: target.role, lineIds: target.lineIds, phone: target.phone, email: target.email, skills: target.skills, password: "", active: target.active });
    else setF(blank());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, target?.id]);

  const set = <K extends keyof typeof f>(key: K, value: (typeof f)[K]) => setF((s) => ({ ...s, [key]: value }));

  const submit = async () => {
    setError(null);
    const emp = f.employeeId.trim();
    const idErr = validateEmployeeId(emp);
    if (idErr) return setError(idErr);
    if (!f.name.trim()) return setError("Name is required");
    if (snapshot.users.some((u) => u.employeeId.toLowerCase() === emp.toLowerCase() && u.id !== target?.id)) return setError(`Employee ID ${emp} already exists`);
    if (!canManageUserRole(actor, f.role)) return setError("You cannot assign that role");
    if (target && target.id === actor.id && f.role !== target.role) return setError("You cannot change your own role");
    if (!target) {
      const pwErr = validatePassword(f.password);
      if (pwErr) return setError(pwErr);
    }
    const now = nowIso();
    const creds = !target ? await hashPassword(f.password) : null;
    const id = target?.id ?? newId();
    mutate(
      (d) => {
        const data = { employeeId: emp, name: f.name.trim(), role: f.role, lineIds: f.role === "production_supervisor" ? f.lineIds : [], phone: f.phone.trim(), email: f.email.trim(), skills: f.skills.trim(), active: f.active, updatedAt: now };
        if (target) {
          const u = d.users.find((x) => x.id === target.id);
          if (u) Object.assign(u, data);
        } else if (creds) {
          d.users.push({ id, ...data, passwordHash: creds.hash, passwordSalt: creds.salt, mustChangePassword: true, failedAttempts: 0, lockedUntil: null, lastLoginAt: null, createdAt: now });
        }
      },
      { entity: "user", entityId: id, action: target ? "update" : "create", summary: `User ${emp} (${ROLE_LABELS[f.role]}) ${target ? "updated" : "created"} by ${actor.name}` },
    );
    if (target) {
      toast.success("User updated");
      onClose();
    } else {
      setCreated({ employeeId: emp, password: f.password });
    }
  };

  if (created) {
    return (
      <Modal title="User created" open={open} onClose={onClose} size="narrow" footer={<Button variant="primary" onClick={onClose}>Done</Button>}>
        <Notice tone="good" icon="check">
          Give these details to the user. The password is shown only once and must be changed at first sign-in.
        </Notice>
        <dl className="kv mt-16">
          <dt>Employee ID</dt>
          <dd className="mono" style={{ fontWeight: 600 }}>{created.employeeId}</dd>
          <dt>Temporary password</dt>
          <dd className="mono" style={{ fontWeight: 600, fontSize: 18 }}>{created.password}</dd>
        </dl>
      </Modal>
    );
  }

  return (
    <Modal
      title={target ? `Edit ${target.employeeId}` : "New user"}
      open={open}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit}>
            {target ? "Save" : "Create user"}
          </Button>
        </>
      }
    >
      <div className="form-grid">
        <Field label="Employee ID" required>
          <input value={f.employeeId} onChange={(e) => set("employeeId", e.target.value)} autoCapitalize="characters" />
        </Field>
        <Field label="Name" required>
          <input value={f.name} onChange={(e) => set("name", e.target.value)} />
        </Field>
        <Field label="Role" required>
          <select value={f.role} onChange={(e) => set("role", e.target.value as Role)} disabled={target?.id === actor.id}>
            {roles.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Phone">
          <input value={f.phone} onChange={(e) => set("phone", e.target.value)} />
        </Field>
        {f.role === "production_supervisor" && (
          <Field label="Lines covered" hint="Leave empty for all lines" className="full">
            <ChipSelect options={snapshot.lines.filter((l) => l.active).map((l) => ({ value: l.id, label: `${l.code} ${l.name}` }))} value={f.lineIds} onChange={(v) => set("lineIds", v)} />
          </Field>
        )}
        <Field label="Email">
          <input type="email" value={f.email} onChange={(e) => set("email", e.target.value)} />
        </Field>
        <Field label="Skills / trade">
          <input value={f.skills} onChange={(e) => set("skills", e.target.value)} placeholder="Electrical, PLC, hydraulics…" />
        </Field>
        {!target && (
          <Field label="Temporary password" required hint="Shown once after creation; the user must change it" className="full">
            <div className="flex">
              <input value={f.password} onChange={(e) => set("password", e.target.value)} className="mono" />
              <Button onClick={() => set("password", tempPassword())}>Generate</Button>
            </div>
          </Field>
        )}
        {target && target.id !== actor.id && (
          <label className="check">
            <input type="checkbox" checked={f.active} onChange={(e) => set("active", e.target.checked)} /> Active
          </label>
        )}
        {error && (
          <div className="full">
            <Notice tone="critical" icon="alert">
              {error}
            </Notice>
          </div>
        )}
      </div>
    </Modal>
  );
}

function ResetPassword({ user: target, onClose }: { user: User | null; onClose: () => void }) {
  const { mutate } = useStore();
  const actor = useCurrentUser();
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (target) {
      setPassword(tempPassword());
      setDone(false);
    }
  }, [target]);
  if (!target) return null;
  const submit = async () => {
    const { hash, salt } = await hashPassword(password);
    mutate(
      (d) => {
        const u = d.users.find((x) => x.id === target.id);
        if (!u) return;
        u.passwordHash = hash;
        u.passwordSalt = salt;
        u.mustChangePassword = true;
        u.failedAttempts = 0;
        u.lockedUntil = null;
        u.updatedAt = nowIso();
      },
      { entity: "user", entityId: target.id, action: "password_reset", summary: `Password reset for ${target.employeeId} by ${actor.name}` },
    );
    setDone(true);
  };
  return (
    <Modal title={`Reset password · ${target.employeeId}`} open onClose={onClose} size="narrow" footer={done ? <Button variant="primary" onClick={onClose}>Done</Button> : <><Button onClick={onClose}>Cancel</Button><Button variant="primary" onClick={submit}>Reset password</Button></>}>
      {done ? (
        <>
          <Notice tone="good" icon="check">
            Password reset and any lock cleared. The user must choose a new password at the next sign-in.
          </Notice>
          <dl className="kv mt-16">
            <dt>Temporary password</dt>
            <dd className="mono" style={{ fontWeight: 600, fontSize: 18 }}>{password}</dd>
          </dl>
        </>
      ) : (
        <Field label="Temporary password" hint="Give it to the user in person">
          <div className="flex">
            <input value={password} onChange={(e) => setPassword(e.target.value)} className="mono" />
            <Button onClick={() => setPassword(tempPassword())}>Generate</Button>
          </div>
        </Field>
      )}
    </Modal>
  );
}
