import { useMutation } from "@tanstack/react-query";
import { UserRound } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { Card, PageHeader } from "@/components/ui";

export function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [profile, setProfile] = useState({
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    email: user?.email ?? "",
    phone: "",
  });
  const [pwd, setPwd] = useState({
    current_password: "",
    new_password: "",
    new_password_confirm: "",
  });
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [pwdMsg, setPwdMsg] = useState<string | null>(null);
  const [pwdError, setPwdError] = useState<string | null>(null);

  const saveProfile = useMutation({
    mutationFn: async () =>
      (await api.patch("/users/me/", {
        first_name: profile.first_name,
        last_name: profile.last_name,
        email: profile.email,
      })).data,
    onSuccess: async () => {
      await refreshUser();
      setProfileMsg("Profil mis à jour.");
    },
    onError: () => setProfileMsg("Impossible d'enregistrer le profil."),
  });

  const changePwd = useMutation({
    mutationFn: async () =>
      (await api.post("/users/me/change-password/", pwd)).data,
    onSuccess: async () => {
      setPwd({
        current_password: "",
        new_password: "",
        new_password_confirm: "",
      });
      setPwdError(null);
      setPwdMsg("Mot de passe mis à jour.");
      await refreshUser();
    },
    onError: (err: unknown) => {
      setPwdMsg(null);
      const data =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: Record<string, unknown> } }).response
              ?.data
          : undefined;
      const msg =
        (data?.current_password as string[] | string | undefined) ||
        (data?.new_password as string[] | string | undefined) ||
        (data?.new_password_confirm as string[] | string | undefined) ||
        (data?.detail as string | undefined) ||
        "Échec du changement de mot de passe.";
      setPwdError(Array.isArray(msg) ? msg.join(" ") : String(msg));
    },
  });

  if (!user) return null;

  function onProfile(e: FormEvent) {
    e.preventDefault();
    setProfileMsg(null);
    saveProfile.mutate();
  }

  function onPassword(e: FormEvent) {
    e.preventDefault();
    setPwdError(null);
    setPwdMsg(null);
    if (pwd.new_password.length < 10) {
      setPwdError("Le nouveau mot de passe doit contenir au moins 10 caractères.");
      return;
    }
    if (pwd.new_password !== pwd.new_password_confirm) {
      setPwdError("Les mots de passe ne correspondent pas.");
      return;
    }
    changePwd.mutate();
  }

  return (
    <div>
      <PageHeader
        icon={UserRound}
        title="Mon profil"
        subtitle={`${user.username} — informations personnelles et sécurité`}
      />

      <Card title="Informations">
        <form className="inline-form" onSubmit={onProfile}>
          <div className="form-grid">
            <label className="field">
              <span>Identifiant</span>
              <input value={user.username} readOnly />
            </label>
            <label className="field">
              <span>Prénom</span>
              <input
                value={profile.first_name}
                onChange={(e) =>
                  setProfile({ ...profile, first_name: e.target.value })
                }
              />
            </label>
            <label className="field">
              <span>Nom</span>
              <input
                value={profile.last_name}
                onChange={(e) =>
                  setProfile({ ...profile, last_name: e.target.value })
                }
              />
            </label>
            <label className="field">
              <span>E-mail *</span>
              <input
                type="email"
                value={profile.email}
                onChange={(e) =>
                  setProfile({ ...profile, email: e.target.value })
                }
                required
              />
            </label>
          </div>
          {profileMsg && <p className="muted small">{profileMsg}</p>}
          <button className="btn btn-primary" disabled={saveProfile.isPending}>
            Enregistrer le profil
          </button>
        </form>
      </Card>

      <Card title="Changer mon mot de passe">
        <form className="inline-form" onSubmit={onPassword}>
          <div className="form-grid">
            <label className="field">
              <span>Mot de passe actuel *</span>
              <input
                type="password"
                value={pwd.current_password}
                onChange={(e) =>
                  setPwd({ ...pwd, current_password: e.target.value })
                }
                required
                autoComplete="current-password"
              />
            </label>
            <label className="field">
              <span>Nouveau mot de passe * (≥ 10 car.)</span>
              <input
                type="password"
                value={pwd.new_password}
                onChange={(e) =>
                  setPwd({ ...pwd, new_password: e.target.value })
                }
                required
                autoComplete="new-password"
              />
            </label>
            <label className="field">
              <span>Confirmation *</span>
              <input
                type="password"
                value={pwd.new_password_confirm}
                onChange={(e) =>
                  setPwd({ ...pwd, new_password_confirm: e.target.value })
                }
                required
                autoComplete="new-password"
              />
            </label>
          </div>
          {pwdError && <div className="form-error">{pwdError}</div>}
          {pwdMsg && <p className="muted small">{pwdMsg}</p>}
          <button className="btn btn-primary" disabled={changePwd.isPending}>
            Mettre à jour le mot de passe
          </button>
        </form>
      </Card>
    </div>
  );
}
