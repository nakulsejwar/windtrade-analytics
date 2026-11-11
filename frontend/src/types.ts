export interface Metrics { n: number; mae: number | null; rmse: number | null; bias: number | null; wape: number | null; maxOver: number | null; maxUnder: number | null; actualIntervals: number; coverage: number }
export interface Quantiles { p05: number | null; p10: number | null; p25: number | null; p50: number | null; p75: number | null; p90: number | null; p95: number | null }
export interface DailyRow { date: string; intervals: number; scored: number; actualAvg: number; forecastAvg: number | null; mae: number | null; bias: number | null; rmse: number | null }
export interface HourRow { hour: number; n: number; mae: number | null; bias: number | null; rmse: number | null }
export interface HorizonRow { fromHours: number; toHours: number; n: number; mae: number | null; bias: number | null; rmse: number | null }
export interface HistBin { from: number; to: number; count: number }
export interface Summary {
  period: { decisionStart: string; decisionEnd: string; deliveryStart: string; deliveryEnd: string; cutoff: string };
  metrics: Metrics; quantiles: Quantiles; histogram: HistBin[]; daily: DailyRow[]; byHour: HourRow[]; byHorizon: HorizonRow[];
  dataSource: string; dataGeneratedAt: string | null;
}
export interface Meta {
  decisionMin: string; decisionMax: string; cutoffPresets: { value: string; label: string }[]; defaultCutoff: string;
  dataSource: string; dataGeneratedAt: string | null; actualIntervals: number; forecastRecords: number;
}
export interface DecisionPoint { startTime: string; forecast: number | null; publishTime: string | null; latestForecast: number | null; actual: number | null; low: number | null; high: number | null }
export interface Decision {
  decisionDate: string; deliveryDate: string; cutoffUtc: string; cutoff: string; points: DecisionPoint[]; errorQuantiles: Quantiles;
  summary: { intervals: number; withForecast: number; avgMW: number | null; minMW: number | null; maxMW: number | null; energyMWh: number | null; vintageFrom: string | null; vintageTo: string | null };
}
export interface Vintage { publishTime: string; intervals: number; forecastAvg: number; mae: number | null; bias: number | null; eligible: boolean; hoursBeforeCutoff: number }
export interface IntervalRow { startTime: string; deliveryDate: string; actual: number; forecast: number | null; error: number | null; publishTime: string | null; leadHours: number | null }
