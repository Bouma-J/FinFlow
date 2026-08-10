import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

import type { CollectionCase } from "@/api/types";

function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "-";
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(n)) return "-";
  return Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function pdfText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\x20-\x7E\xA0-\xFF]/g, "")
    .replace(/[\u00A0\u202F\u2009]/g, " ");
}

export function exportCollectionCasePdf(c: CollectionCase): void {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const title = pdfText(
    `Recouvrement — ${c.application_reference || c.client_name}`,
  );
  doc.setFontSize(14);
  doc.text(title, 14, 16);
  doc.setFontSize(10);
  doc.text(pdfText(`${c.client_name} · ${c.agency_name}`), 14, 22);
  doc.text(
    pdfText(
      `PAR ${c.par_class_display} · ${c.stage_display} · ${c.days_overdue} j · Impaye ${money(c.overdue_amount)}`,
    ),
    14,
    28,
  );

  autoTable(doc, {
    startY: 34,
    head: [["N", "Echeance", "Du", "Paye", "Reste", "Statut"]],
    body: (c.installments || []).map((i) => [
      String(i.number),
      i.due_date,
      money(i.total_due),
      money(i.amount_paid),
      money(i.balance),
      pdfText(i.status_display),
    ]),
    styles: { fontSize: 8 },
    headStyles: { fillColor: [15, 148, 136] },
  });

  const afterSchedule = (doc as jsPDF & { lastAutoTable?: { finalY: number } })
    .lastAutoTable?.finalY;
  let y = (afterSchedule || 40) + 8;
  doc.setFontSize(11);
  doc.text("Actions", 14, y);
  y += 2;
  autoTable(doc, {
    startY: y,
    head: [["Date", "Type", "Resultat"]],
    body: (c.actions || []).slice(0, 25).map((a) => [
      a.action_date,
      pdfText(a.action_type_display),
      pdfText(a.result || a.comment || "-"),
    ]),
    styles: { fontSize: 8 },
    headStyles: { fillColor: [15, 148, 136] },
  });

  const ref = (c.application_reference || c.id).replace(/[^\w-]+/g, "_");
  doc.save(`recouvrement_${ref}.pdf`);
}
