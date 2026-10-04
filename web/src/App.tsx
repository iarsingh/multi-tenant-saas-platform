import React, { useEffect, useState } from "react";

type Record = { id: string; tenant: string; title: string; created_by: string };
type Me = { sub: string; tenant: string; role: string; permissions: string[] };

export function App({ token }: { token: string }) {
  const [me, setMe] = useState<Me | null>(null);
  const [records, setRecords] = useState<Record[]>([]);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");

  const headers = (tenant: string) => ({
    Authorization: `Bearer ${token}`,
    "X-Tenant": tenant,
    "content-type": "application/json",
  });

  const load = async (who: Me) => {
    const response = await fetch("/records", { headers: headers(who.tenant) });
    setRecords((await response.json()).records);
  };

  useEffect(() => {
    fetch("/me", { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.json())
      .then((body: Me) => {
        setMe(body);
        load(body);
      });
  }, [token]);

  if (!me) return <p>Signing in</p>;

  const create = async () => {
    const response = await fetch("/records", { method: "POST", headers: headers(me.tenant), body: JSON.stringify({ title }) });
    if (!response.ok) setError((await response.json()).detail);
    else {
      setError("");
      setTitle("");
      load(me);
    }
  };

  return (
    <main>
      <h1>{me.tenant} tenant</h1>
      <p>
        Signed in as {me.sub}, role {me.role}
      </p>
      <ul>
        {records.map((row) => (
          <li key={row.id}>
            {row.title} <small>by {row.created_by}</small>
          </li>
        ))}
      </ul>
      {me.permissions.includes("create") && (
        <div>
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
          <button onClick={create}>Add</button>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
