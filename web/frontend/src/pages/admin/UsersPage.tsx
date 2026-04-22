import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { createUser, listUsers, updateUser } from "@/api/auth";
import { Badge, Button, Card, Input, Label } from "@/components/ui";

export default function UsersPage() {
  const qc = useQueryClient();
  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: listUsers,
  });
  const [showCreate, setShowCreate] = useState(false);

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateUser(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Brukere</h1>
          <p className="text-sm text-slate-500">
            Opprett kontoer og kontroller tilgang.
          </p>
        </div>
        <Button onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "Lukk skjema" : "+ Ny bruker"}
        </Button>
      </div>

      {showCreate && <CreateUserForm onDone={() => setShowCreate(false)} />}

      <div className="mt-6 space-y-2">
        {users.map((u) => (
          <Card key={u.id} className="flex items-center justify-between p-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium">{u.name}</span>
                <Badge tone={u.role === "admin" ? "blue" : "neutral"}>
                  {u.role}
                </Badge>
                {!u.is_active && <Badge tone="red">deaktivert</Badge>}
              </div>
              <div className="mt-1 text-sm text-slate-500">{u.email}</div>
            </div>
            <Button
              size="sm"
              variant={u.is_active ? "secondary" : "primary"}
              onClick={() =>
                toggleMutation.mutate({ id: u.id, is_active: !u.is_active })
              }
            >
              {u.is_active ? "Deaktiver" : "Reaktiver"}
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}

function CreateUserForm({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"user" | "admin">("user");

  const createMutation = useMutation({
    mutationFn: () => createUser({ email, name, password, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      onDone();
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    createMutation.mutate();
  }

  return (
    <Card className="p-5">
      <form onSubmit={submit} className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="nu-email">E-post</Label>
          <Input
            id="nu-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="nu-name">Navn</Label>
          <Input
            id="nu-name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="nu-pw">Passord (min 8 tegn)</Label>
          <Input
            id="nu-pw"
            type="password"
            minLength={8}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="nu-role">Rolle</Label>
          <select
            id="nu-role"
            value={role}
            onChange={(e) => setRole(e.target.value as "user" | "admin")}
            className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </div>
        {createMutation.isError && (
          <div className="col-span-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {(createMutation.error as { response?: { data?: { detail?: string } } })
              .response?.data?.detail ?? "Kunne ikke opprette"}
          </div>
        )}
        <div className="col-span-2 flex gap-2">
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Oppretter…" : "Opprett"}
          </Button>
          <Button type="button" variant="secondary" onClick={onDone}>
            Avbryt
          </Button>
        </div>
      </form>
    </Card>
  );
}
