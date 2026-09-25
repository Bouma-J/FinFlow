import { BarChart3, Table2 } from "lucide-react";

interface FieldModeToggleProps {
  mode: "SYNTHETIC" | "DETAILED";
  onModeChange: (mode: "SYNTHETIC" | "DETAILED") => void;
  disabled?: boolean;
}

export function FieldModeToggle({
  mode,
  onModeChange,
  disabled = false,
}: FieldModeToggleProps) {
  return (
    <div style={{
      marginBottom: '1.5rem',
      padding: '1rem',
      backgroundColor: '#f9fafb',
      border: '1px solid #e5e7eb',
      borderRadius: '0.5rem'
    }}>
      <div style={{ marginBottom: '0.75rem' }}>
        <span className="text-sm font-medium text-gray-700">Mode de saisie</span>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <button
          type="button"
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            padding: '0.75rem 1rem',
            backgroundColor: mode === "SYNTHETIC" ? '#3b82f6' : 'white',
            border: `2px solid ${mode === "SYNTHETIC" ? '#3b82f6' : '#d1d5db'}`,
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            fontWeight: 500,
            color: mode === "SYNTHETIC" ? 'white' : '#6b7280',
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
            opacity: disabled ? 0.5 : 1
          }}
          onClick={() => onModeChange("SYNTHETIC")}
          disabled={disabled}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Synthétique</span>
        </button>
        <button
          type="button"
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            padding: '0.75rem 1rem',
            backgroundColor: mode === "DETAILED" ? '#3b82f6' : 'white',
            border: `2px solid ${mode === "DETAILED" ? '#3b82f6' : '#d1d5db'}`,
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            fontWeight: 500,
            color: mode === "DETAILED" ? 'white' : '#6b7280',
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
            opacity: disabled ? 0.5 : 1
          }}
          onClick={() => onModeChange("DETAILED")}
          disabled={disabled}
        >
          <Table2 className="w-4 h-4" />
          <span>Détaillé</span>
        </button>
      </div>
      <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
        {mode === "SYNTHETIC" ? (
          <>
            <span style={{ fontWeight: 500 }}>Synthétique :</span> Saisir des montants
            moyens ou totaux
          </>
        ) : (
          <>
            <span style={{ fontWeight: 500 }}>Détaillé :</span> Détailler les montants
            pour chaque période (mois, trimestre)
          </>
        )}
      </p>
    </div>
  );
}
