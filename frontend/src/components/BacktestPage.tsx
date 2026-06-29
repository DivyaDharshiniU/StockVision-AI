import { useState } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import DatePicker from "@cloudscape-design/components/date-picker";
import Button from "@cloudscape-design/components/button";
import Spinner from "@cloudscape-design/components/spinner";
import Alert from "@cloudscape-design/components/alert";
import { BacktestResult } from "../types";
import PrecisionRecallPanel from "./PrecisionRecallPanel";
import BacktestTable from "./BacktestTable";
import BacktestChart from "./BacktestChart";

export default function BacktestPage() {
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

  const runBacktest = async () => {
    if (!selectedDate) {
      setError("Please select a date");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch(`${base}/api/backtest?date=${selectedDate}`);
      if (!r.ok) {
        const body = await r.json();
        throw new Error(body.error || `HTTP ${r.status}`);
      }
      setResult(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return (
    <SpaceBetween size="l">
      <Container header={<Header variant="h2">Backtest Evaluation</Header>}>
        <SpaceBetween size="m" direction="horizontal">
          <DatePicker
            value={selectedDate}
            onChange={({ detail }) => setSelectedDate(detail.value)}
            placeholder="YYYY-MM-DD"
            isDateEnabled={(date) => {
              const d = new Date(date.toISOString());
              d.setHours(0, 0, 0, 0);
              return d < today;
            }}
          />
          <Button variant="primary" onClick={runBacktest} loading={loading}>
            Run Backtest
          </Button>
        </SpaceBetween>
      </Container>

      {error && (
        <Alert type="error" header="Backtest error">
          {error}
        </Alert>
      )}
      {loading && <Spinner size="large" />}

      {result && (
        <SpaceBetween size="l">
          <PrecisionRecallPanel precisionRecall={result.precision_recall} />
          <BacktestTable picks={result.picks} />
          <BacktestChart
            picks={result.picks}
            benchmarkReturns={result.benchmark_returns}
          />
        </SpaceBetween>
      )}
    </SpaceBetween>
  );
}
