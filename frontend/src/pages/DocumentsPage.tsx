import { useQuery } from "@tanstack/react-query";
import { Download, FolderOpen, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { DocumentCategory, GedDocument, Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Card,
  PageHeader,
  PaginationBar,
  QueryStatus,
  TenantScopeNotice,
  formatDate,
} from "@/components/ui";

function formatBytes(n: number) {
  if (!n || n < 0) return "—";
  if (n < 1024) return `${n} o`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`;
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`;
}

function relatedHref(doc: GedDocument): string | null {
  if (doc.related_path) return doc.related_path;
  const t = doc.related_type || "";
  if (!doc.object_id) return null;
  if (t.includes("creditapplication")) return `/dossiers/${doc.object_id}`;
  if (t.includes("guaranteereleaserequest"))
    return `/mains-levees/${doc.object_id}`;
  if (t.includes("dationrequest")) return `/dations/${doc.object_id}`;
  if (t.includes("guaranteeformalizationrequest"))
    return `/formalisations/${doc.object_id}`;
  if (t.includes("collectioncase")) return `/recouvrement/${doc.object_id}`;
  // litigationfile sans related_path : pas de caseId → pas de lien trompeur
  if (t.includes("litigationfile")) return null;
  if (t.includes("guarantee") && !t.includes("request"))
    return `/garanties/${doc.object_id}`;
  return null;
}

export function DocumentsPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState("");
  const [expiringOnly, setExpiringOnly] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 280);
    return () => clearTimeout(t);
  }, [search]);

  const categories = useQuery({
    queryKey: ["document-categories", activeTenant],
    queryFn: async () =>
      (
        await api.get<Paginated<DocumentCategory>>("/document-categories/", {
          params: { page_size: 200, is_active: true },
        })
      ).data,
    enabled: !needsTenant,
  });

  const docs = useQuery({
    queryKey: [
      "ged-documents",
      activeTenant,
      page,
      debounced,
      category,
      expiringOnly,
    ],
    queryFn: async () => {
      if (expiringOnly) {
        return (
          await api.get<Paginated<GedDocument> | GedDocument[]>(
            "/documents/expiring_soon/",
            { params: { page, page_size: 25 } },
          )
        ).data;
      }
      return (
        await api.get<Paginated<GedDocument>>("/documents/", {
          params: {
            page,
            page_size: 25,
            ...(debounced ? { search: debounced } : {}),
            ...(category ? { category } : {}),
          },
        })
      ).data;
    },
    enabled: !needsTenant,
  });

  if (needsTenant) {
    return (
      <div className="page-shell">
        <PageHeader
          icon={FolderOpen}
          title="GED"
          subtitle="Consultation des documents"
        />
        <TenantScopeNotice />
      </div>
    );
  }

  const results: GedDocument[] = Array.isArray(docs.data)
    ? docs.data
    : (docs.data?.results ?? []);
  const count = Array.isArray(docs.data)
    ? docs.data.length
    : (docs.data?.count ?? 0);

  return (
    <div>
      <PageHeader
        icon={FolderOpen}
        title="GED — Documents"
        subtitle="Consultation unifiée (crédits, formalisations, mains levées, dations, contentieux)"
      />

      <Card title="Filtres">
        <div className="form-grid" style={{ alignItems: "end" }}>
          <label className="field">
            <span>
              <Search size={13} style={{ verticalAlign: "-2px", marginRight: 4 }} />
              Recherche
            </span>
            <input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Nom de fichier, catégorie…"
            />
          </label>
          <label className="field">
            <span>Catégorie</span>
            <select
              value={category}
              disabled={expiringOnly}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Toutes</option>
              {(categories.data?.results ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Expirant ≤ 30 j</span>
            <input
              type="checkbox"
              checked={expiringOnly}
              onChange={(e) => {
                setExpiringOnly(e.target.checked);
                setPage(1);
              }}
            />
          </label>
        </div>
        <p className="muted small" style={{ marginTop: 10 }}>
          Les catégories se paramètrent dans{" "}
          <Link to="/admin/referentiels-metier">Référentiels métier</Link>.
          Les pièces dossier sont aussi indexées ici à l&apos;upload.
        </p>
      </Card>

      <Card title="Documents">
        <QueryStatus
          isLoading={docs.isLoading}
          isError={docs.isError}
          isEmpty={results.length === 0}
          emptyMessage="Aucun document dans la GED pour ces filtres."
          onRetry={() => docs.refetch()}
        >
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Catégorie</th>
                  <th>Rattaché à</th>
                  <th>Taille</th>
                  <th>Créé le</th>
                  <th>Expire</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {results.map((d) => {
                  const href = relatedHref(d);
                  const url = d.file_url || d.file;
                  return (
                    <tr key={d.id}>
                      <td>
                        <strong>{d.name}</strong>
                        {d.uploaded_by_name ? (
                          <div className="muted small">{d.uploaded_by_name}</div>
                        ) : null}
                      </td>
                      <td>
                        <code>{d.category_code || "—"}</code>
                        <div className="muted small">{d.category_label}</div>
                      </td>
                      <td>
                        {href && d.related_label ? (
                          <Link to={href}>{d.related_label}</Link>
                        ) : (
                          d.related_label || (
                            <span className="muted">—</span>
                          )
                        )}
                      </td>
                      <td>{formatBytes(d.size_bytes)}</td>
                      <td>{formatDate(d.created_at)}</td>
                      <td>
                        {d.expiry_date ? formatDate(d.expiry_date) : "—"}
                      </td>
                      <td>
                        {url ? (
                          <a
                            className="btn btn-ghost btn-sm"
                            href={url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            <Download size={14} />
                            Ouvrir
                          </a>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!expiringOnly && (
              <PaginationBar
                page={page}
                count={count}
                onPageChange={setPage}
              />
            )}
          </>
        </QueryStatus>
      </Card>
    </div>
  );
}
