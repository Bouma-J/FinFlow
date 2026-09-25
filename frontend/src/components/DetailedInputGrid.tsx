interface DetailedField {
  key: string;
  label: string;
  format?: "money" | "number" | "percent";
}

interface DetailedInputGridProps {
  periods: number;
  periodLabels: string[];
  fields: DetailedField[];
  values: Record<string, number>[];
  onChange: (periodIndex: number, fieldKey: string, value: number) => void;
  showAverage?: boolean;
  currency?: string;
}

export function DetailedInputGrid({
  periods,
  periodLabels,
  fields,
  values,
  onChange,
  showAverage = true,
  currency = "XOF",
}: DetailedInputGridProps) {
  const calculateAverage = (fieldKey: string): number => {
    const sum = values.reduce(
      (acc, period) => acc + (period[fieldKey] || 0),
      0
    );
    return sum / periods;
  };

  const formatValue = (value: number, format?: string): string => {
    if (format === "money") {
      return new Intl.NumberFormat("fr-FR", {
        style: "decimal",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);
    }
    if (format === "percent") {
      return `${value.toFixed(1)}%`;
    }
    return value.toLocaleString("fr-FR");
  };

  return (
    <div style={{ overflowX: "auto", marginTop: "1rem" }}>
      <table style={{
        width: "100%",
        borderCollapse: "collapse",
        fontSize: "0.875rem",
        backgroundColor: "white",
        border: "1px solid #e5e7eb",
        borderRadius: "0.5rem"
      }}>
        <thead>
          <tr style={{ backgroundColor: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
            <th style={{
              padding: "0.75rem",
              textAlign: "left",
              fontWeight: 600,
              color: "#374151",
              position: "sticky",
              left: 0,
              backgroundColor: "#f9fafb",
              zIndex: 10
            }}>
              Poste
            </th>
            {periodLabels.map((label, idx) => (
              <th
                key={idx}
                style={{
                  padding: "0.75rem",
                  textAlign: "right",
                  fontWeight: 600,
                  color: "#374151",
                  minWidth: "120px"
                }}
              >
                {label}
              </th>
            ))}
            {showAverage && (
              <th style={{
                padding: "0.75rem",
                textAlign: "right",
                fontWeight: 600,
                color: "#374151",
                backgroundColor: "#eff6ff",
                minWidth: "120px"
              }}>
                Moyenne
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {fields.map((field, fieldIdx) => (
            <tr
              key={field.key}
              style={{
                borderBottom: fieldIdx < fields.length - 1 ? "1px solid #e5e7eb" : "none",
                backgroundColor: fieldIdx % 2 === 0 ? "white" : "#f9fafb"
              }}
            >
              <td style={{
                padding: "0.75rem",
                fontWeight: 500,
                color: "#374151",
                position: "sticky",
                left: 0,
                backgroundColor: fieldIdx % 2 === 0 ? "white" : "#f9fafb",
                zIndex: 5
              }}>
                {field.label}
              </td>
              {values.map((period, periodIdx) => (
                <td key={periodIdx} style={{ padding: "0.5rem" }}>
                  <input
                    type="number"
                    value={period[field.key] || 0}
                    onChange={(e) =>
                      onChange(
                        periodIdx,
                        field.key,
                        parseFloat(e.target.value) || 0
                      )
                    }
                    style={{
                      width: "100%",
                      padding: "0.5rem",
                      border: "1px solid #d1d5db",
                      borderRadius: "0.375rem",
                      fontSize: "0.875rem",
                      textAlign: "right"
                    }}
                    step="any"
                  />
                </td>
              ))}
              {showAverage && (
                <td style={{
                  padding: "0.75rem",
                  textAlign: "right",
                  fontWeight: 600,
                  color: "#1f2937",
                  backgroundColor: "#eff6ff"
                }}>
                  {formatValue(calculateAverage(field.key), field.format)}
                  {field.format === "money" && ` ${currency}`}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{
        marginTop: "0.75rem",
        padding: "0.75rem",
        backgroundColor: "#f0f9ff",
        border: "1px solid #bfdbfe",
        borderRadius: "0.375rem",
        fontSize: "0.875rem",
        color: "#1e40af"
      }}>
        <strong>💡 Astuce :</strong> Les moyennes calculées automatiquement seront
        utilisées pour les indicateurs et les ratios.
      </div>
    </div>
  );
}
