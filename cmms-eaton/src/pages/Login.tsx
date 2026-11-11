import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ChangePasswordModal } from "../components/Layout";
import { Button, Field, Notice } from "../components/ui";
import { hashPassword, validateEmployeeId, validatePassword } from "../lib/auth";
import { newId, nowIso } from "../lib/ids";
import { homeRouteFor } from "../lib/permissions";
import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "../store/seed";
import { useStore } from "../store/StoreProvider";
import { ROLE_LABELS } from "../types";

export function Login() {
  const { ready, snapshot, user, login, mutate } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const from = (location.state as { from?: string } | null)?.from;

  useEffect(() => {
    if (user && !user.mustChangePassword) navigate(from && from !== "/login" ? from : homeRouteFor(user.role), { replace: true });
  }, [user, navigate, from]);

  if (!ready) return null;
  if (snapshot.users.length === 0) return <FirstRun />;
  if (user && user.mustChangePassword) {
    return (
      <div className="login">
        <ChangePasswordModal open forced onClose={() => navigate(homeRouteFor(user.role), { replace: true })} />
      </div>
    );
  }
  if (user) return <Navigate to={homeRouteFor(user.role)} replace />;

  const submit = async () => {
    setBusy(true);
    setError(null);
    const res = await login(employeeId, password);
    setBusy(false);
    if (!res.ok) setError(res.message);
  };

  const demoLogin = async (id: string) => {
    setEmployeeId(id);
    setPassword(DEMO_PASSWORD);
    setBusy(true);
    const res = await login(id, DEMO_PASSWORD);
    setBusy(false);
    if (!res.ok) setError(res.message);
  };

  const demoUsersPresent = snapshot.demo && DEMO_ACCOUNTS.some((a) => snapshot.users.some((u) => u.employeeId === a.employeeId));

  return (
    <div className="login">
      <div className="card">
        <div className="card-body">
          <div className="brand">
            <img src="/icon.svg" alt="" />
            <div>
              CMMS_Eaton
              <small>{snapshot.settings.plantName}</small>
            </div>
          </div>
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <Field label="Employee ID" required>
              <input value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} autoComplete="username" autoFocus autoCapitalize="characters" />
            </Field>
            <Field label="Password" required error={error}>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </Field>
            <Button type="submit" variant="primary" className="block" disabled={busy || !employeeId || !password}>
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
          {demoUsersPresent && (
            <div className="demo-accounts">
              <p className="muted">Sample accounts (password {DEMO_PASSWORD}). Replace them in Settings before going live.</p>
              <table>
                <tbody>
                  {DEMO_ACCOUNTS.map((a) => (
                    <tr key={a.employeeId}>
                      <td>
                        <button type="button" onClick={() => demoLogin(a.employeeId)}>
                          {a.employeeId}
                        </button>
                      </td>
                      <td>{a.name}</td>
                      <td className="muted">{ROLE_LABELS[a.role]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  function FirstRun() {
    const [name, setName] = useState("");
    const [emp, setEmp] = useState("");
    const [pw, setPw] = useState("");
    const [pw2, setPw2] = useState("");
    const [plant, setPlant] = useState(snapshot.settings.plantName);
    const [err, setErr] = useState<string | null>(null);
    const [working, setWorking] = useState(false);

    const create = async () => {
      setErr(null);
      const idErr = validateEmployeeId(emp);
      if (idErr) return setErr(idErr);
      if (!name.trim()) return setErr("Enter your name");
      const pwErr = validatePassword(pw);
      if (pwErr) return setErr(pwErr);
      if (pw !== pw2) return setErr("Passwords do not match");
      setWorking(true);
      const { hash, salt } = await hashPassword(pw);
      const now = nowIso();
      const id = newId();
      mutate(
        (d) => {
          d.settings.plantName = plant.trim() || d.settings.plantName;
          d.users.push({
            id,
            employeeId: emp.trim(),
            name: name.trim(),
            role: "owner",
            lineIds: [],
            phone: "",
            email: "",
            skills: "",
            active: true,
            passwordHash: hash,
            passwordSalt: salt,
            mustChangePassword: false,
            failedAttempts: 0,
            lockedUntil: null,
            lastLoginAt: null,
            createdAt: now,
            updatedAt: now,
          });
        },
        { entity: "user", entityId: id, action: "create", summary: `Owner account ${emp.trim()} created` },
      );
      setWorking(false);
    };

    return (
      <div className="login">
        <div className="card">
          <div className="card-body">
            <div className="brand">
              <img src="/icon.svg" alt="" />
              <div>
                CMMS_Eaton
                <small>First run: create the owner account</small>
              </div>
            </div>
            <Notice tone="accent" icon="info">
              This account manages every user and setting. Technicians and supervisors are added later under Users.
            </Notice>
            <form
              className="stack mt-16"
              onSubmit={(e) => {
                e.preventDefault();
                create();
              }}
            >
              <Field label="Plant name">
                <input value={plant} onChange={(e) => setPlant(e.target.value)} />
              </Field>
              <Field label="Your name" required>
                <input value={name} onChange={(e) => setName(e.target.value)} />
              </Field>
              <Field label="Employee ID" required>
                <input value={emp} onChange={(e) => setEmp(e.target.value)} autoCapitalize="characters" />
              </Field>
              <Field label="Password" required hint="At least 8 characters">
                <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" />
              </Field>
              <Field label="Confirm password" required error={err}>
                <input type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} autoComplete="new-password" />
              </Field>
              <Button type="submit" variant="primary" className="block" disabled={working}>
                Create owner account
              </Button>
            </form>
          </div>
        </div>
      </div>
    );
  }
}
