const fs = require("fs");
const https = require("https");
const path = require("path");

const CONFIG = {
  start: "2012-01-01",
  end: "2025-12-31",
  monthlyContribution: 1500,
  outputDir: path.join(__dirname, "outputs"),
  qqqSignal: {
    smaPeriod: 200,
    rsiPeriod: 14,
    rsiThreshold: 50,
  },
  tqqqOption: {
    dteDays: 33,
    putStrikePct: 0.92,
    callStrikeMode: "original_put_strike",
    ivLookbackDays: 63,
    ivMultiplier: 1.1,
    minIv: 0.35,
    maxIv: 1.5,
    riskFreeRate: 0.03,
    contractMultiplier: 100,
    roundStrikeTo: 1,
  },
  stage1: {
    initialCapital: 20000,
    stopAtEquity: 100000,
  },
  stage2: {
    initialCapital: 100000,
    age: 30,
    cashPct: 0.1,
    wheelPct: 0.32,
    leapsPct: 0.08,
  },
  leaps: {
    qqqProxySymbol: "QQQ",
    dteDays: 730,
    rollWhenDaysLeft: 365,
    targetDelta: 0.8,
    ivLookbackDays: 252,
    ivMultiplier: 1.1,
    minIv: 0.15,
    maxIv: 0.6,
    riskFreeRate: 0.03,
    contractMultiplier: 100,
    roundStrikeTo: 1,
  },
};

function toUnix(date) {
  return Math.floor(Date.parse(`${date}T00:00:00Z`) / 1000);
}

function addUtcDays(date, days) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function dayDiff(a, b) {
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86400000);
}

function monthKey(date) {
  return date.slice(0, 7);
}

function roundTo(value, step) {
  return Math.max(step, Math.round(value / step) * step);
}

function httpsGetJson(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, { headers: { "User-Agent": "Mozilla/5.0" } }, (res) => {
        let data = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          data += chunk;
        });
        res.on("end", () => {
          if (res.statusCode < 200 || res.statusCode >= 300) {
            reject(new Error(`HTTP ${res.statusCode}: ${data.slice(0, 300)}`));
            return;
          }
          try {
            resolve(JSON.parse(data));
          } catch (err) {
            reject(err);
          }
        });
      })
      .on("error", reject);
  });
}

async function fetchYahooChart(symbol, start, end) {
  const period1 = toUnix(start);
  const period2 = toUnix(addUtcDays(end, 1));
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?period1=${period1}&period2=${period2}&interval=1d&events=history%2Csplits&includeAdjustedClose=true`;
  const json = await httpsGetJson(url);
  const result = json.chart?.result?.[0];
  if (!result) {
    throw new Error(`No Yahoo chart result for ${symbol}: ${JSON.stringify(json.chart?.error || null)}`);
  }
  const quote = result.indicators.quote[0];
  const adj = result.indicators.adjclose[0].adjclose;
  const splits = Object.values(result.events?.splits || {})
    .map((event) => ({
      date: event.date,
      ratio: event.numerator / event.denominator,
    }))
    .sort((a, b) => a.date - b.date);
  const rows = result.timestamp
    .map((ts, i) => {
      const close = quote.close[i];
      const adjClose = adj[i];
      if (!Number.isFinite(close) || !Number.isFinite(adjClose)) return null;
      return {
        ts,
        date: new Date(ts * 1000).toISOString().slice(0, 10),
        close,
        adjClose,
      };
    })
    .filter(Boolean);
  let splitIndex = splits.length - 1;
  let factor = 1;
  for (let i = rows.length - 1; i >= 0; i--) {
    while (splitIndex >= 0 && splits[splitIndex].date > rows[i].ts) {
      factor *= splits[splitIndex].ratio;
      splitIndex -= 1;
    }
    rows[i].nominalClose = rows[i].close * factor;
  }
  return rows;
}

function computeSma(rows, period, key, outputKey) {
  let sum = 0;
  for (let i = 0; i < rows.length; i++) {
    sum += rows[i][key];
    if (i >= period) sum -= rows[i - period][key];
    if (i >= period - 1) rows[i][outputKey] = sum / period;
  }
}

function computeRsi(rows, period, key, outputKey) {
  let gains = 0;
  let losses = 0;
  for (let i = 1; i <= period; i++) {
    const change = rows[i][key] - rows[i - 1][key];
    if (change >= 0) gains += change;
    else losses -= change;
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  rows[period][outputKey] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  for (let i = period + 1; i < rows.length; i++) {
    const change = rows[i][key] - rows[i - 1][key];
    const gain = Math.max(change, 0);
    const loss = Math.max(-change, 0);
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    rows[i][outputKey] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
}

function computeRealizedIv(rows, lookback, multiplier, minIv, maxIv, outputKey, priceKey) {
  const returns = rows.map((row, i) => {
    if (i === 0) return null;
    return Math.log(row[priceKey] / rows[i - 1][priceKey]);
  });
  for (let i = lookback; i < rows.length; i++) {
    const window = returns.slice(i - lookback + 1, i + 1).filter(Number.isFinite);
    const mean = window.reduce((sum, x) => sum + x, 0) / window.length;
    const variance = window.reduce((sum, x) => sum + (x - mean) ** 2, 0) / Math.max(window.length - 1, 1);
    const realized = Math.sqrt(variance) * Math.sqrt(252);
    rows[i][outputKey] = Math.min(maxIv, Math.max(minIv, realized * multiplier));
  }
}

function buildMarketRows(qqqRows, tqqqRows) {
  const qqqMap = new Map(qqqRows.map((row) => [row.date, row]));
  const qqqIndexMap = new Map(qqqRows.map((row, i) => [row.date, i]));
  const rows = [];
  for (const tRow of tqqqRows) {
    const qRow = qqqMap.get(tRow.date);
    if (!qRow) continue;
    const qIndex = qqqIndexMap.get(tRow.date);
    const prevQRow = qIndex > 0 ? qqqRows[qIndex - 1] : null;
    rows.push({
      date: tRow.date,
      qqqClose: qRow.close,
      qqqNominalClose: qRow.nominalClose,
      tqqqClose: tRow.nominalClose,
      qqqSma200: qRow.qqqSma200,
      qqqRsi14: qRow.qqqRsi14,
      qqqIv: qRow.qqqIv,
      tqqqIv: tRow.tqqqIv,
      qqqDownDay: prevQRow ? qRow.close < prevQRow.close : false,
    });
  }
  return rows.filter((row) => row.date >= CONFIG.start && row.date <= CONFIG.end);
}

function erf(x) {
  const sign = x < 0 ? -1 : 1;
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;
  const ax = Math.abs(x);
  const t = 1 / (1 + p * ax);
  const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-ax * ax);
  return sign * y;
}

function normCdf(x) {
  return 0.5 * (1 + erf(x / Math.SQRT2));
}

function invNorm(p) {
  if (p <= 0 || p >= 1) throw new Error("p must be between 0 and 1");
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const plow = 0.02425;
  const phigh = 1 - plow;
  if (p < plow) {
    const q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p > phigh) {
    const q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  const q = p - 0.5;
  const r = q * q;
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
    (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

function callPrice(s, k, t, r, sigma) {
  if (t <= 0) return Math.max(s - k, 0);
  const sqrtT = Math.sqrt(t);
  const d1 = (Math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * sqrtT);
  const d2 = d1 - sigma * sqrtT;
  return s * normCdf(d1) - k * Math.exp(-r * t) * normCdf(d2);
}

function putPrice(s, k, t, r, sigma) {
  if (t <= 0) return Math.max(k - s, 0);
  const sqrtT = Math.sqrt(t);
  const d1 = (Math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * sqrtT);
  const d2 = d1 - sigma * sqrtT;
  return k * Math.exp(-r * t) * normCdf(-d2) - s * normCdf(-d1);
}

function strikeForTargetCallDelta(s, targetDelta, t, r, sigma, roundStep) {
  const d1 = invNorm(targetDelta);
  const raw = s / Math.exp(d1 * sigma * Math.sqrt(t) - (r + 0.5 * sigma * sigma) * t);
  return roundTo(raw, roundStep);
}

function signalAllowsShortPut(row) {
  return Number.isFinite(row.qqqSma200)
    && Number.isFinite(row.qqqRsi14)
    && row.qqqClose > row.qqqSma200
    && row.qqqRsi14 < CONFIG.qqqSignal.rsiThreshold
    && row.qqqDownDay;
}

function optionDaysLeft(rowDate, expiryDate) {
  return Math.max(0, dayDiff(rowDate, expiryDate));
}

function priceShortWheelOption(row, position) {
  const daysLeft = optionDaysLeft(row.date, position.expiryDate);
  const t = daysLeft / 365.25;
  const sigma = row.tqqqIv || CONFIG.tqqqOption.minIv;
  if (position.kind === "short_put") {
    return -putPrice(row.tqqqClose, position.strike, t, CONFIG.tqqqOption.riskFreeRate, sigma) * CONFIG.tqqqOption.contractMultiplier * position.qty;
  }
  return -callPrice(row.tqqqClose, position.strike, t, CONFIG.tqqqOption.riskFreeRate, sigma) * CONFIG.tqqqOption.contractMultiplier * position.qty;
}

function priceLeapsOption(row, leapsPosition) {
  const daysLeft = optionDaysLeft(row.date, leapsPosition.expiryDate);
  const t = daysLeft / 365.25;
  const sigma = row.qqqIv || CONFIG.leaps.minIv;
  return callPrice(row.qqqNominalClose, leapsPosition.strike, t, CONFIG.leaps.riskFreeRate, sigma) * CONFIG.leaps.contractMultiplier * leapsPosition.qty;
}

function maxDrawdownFromSeries(series) {
  let peak = -Infinity;
  let maxDrawdown = 0;
  for (const point of series) {
    peak = Math.max(peak, point.equity);
    if (peak > 0) maxDrawdown = Math.min(maxDrawdown, (point.equity - peak) / peak);
  }
  return maxDrawdown;
}

function xnpv(rate, cashflows) {
  const baseDate = cashflows[0].date;
  return cashflows.reduce((sum, flow) => {
    const years = dayDiff(baseDate, flow.date) / 365.25;
    return sum + flow.amount / (1 + rate) ** years;
  }, 0);
}

function xirr(cashflows) {
  let low = -0.9999;
  let high = 10;
  let npvLow = xnpv(low, cashflows);
  let npvHigh = xnpv(high, cashflows);
  while (npvLow * npvHigh > 0 && high < 1e6) {
    high *= 2;
    npvHigh = xnpv(high, cashflows);
  }
  if (npvLow * npvHigh > 0) return null;
  for (let i = 0; i < 200; i++) {
    const mid = (low + high) / 2;
    const npvMid = xnpv(mid, cashflows);
    if (Math.abs(npvMid) < 1e-8) return mid;
    if (npvLow * npvMid <= 0) {
      high = mid;
      npvHigh = npvMid;
    } else {
      low = mid;
      npvLow = npvMid;
    }
  }
  return (low + high) / 2;
}

function runStage1(rows) {
  let cash = CONFIG.stage1.initialCapital;
  let wheelPosition = null;
  let shares = 0;
  let shareCostBasis = 0;
  let currentMonth = null;
  let cycles = 0;
  let assignedCount = 0;
  let stopLosses = 0;
  const trades = [];
  const equityCurve = [];
  let reachedDate = null;
  const cashflows = [{ date: rows[0].date, amount: -CONFIG.stage1.initialCapital }];

  for (const row of rows) {
    if (currentMonth !== monthKey(row.date)) {
      currentMonth = monthKey(row.date);
      if (row.date > CONFIG.start) {
        cash += CONFIG.monthlyContribution;
        cashflows.push({ date: row.date, amount: -CONFIG.monthlyContribution });
      }
    }

    if (wheelPosition && row.date >= wheelPosition.expiryDate) {
      if (wheelPosition.kind === "short_put") {
        if (row.tqqqClose >= wheelPosition.strike) {
          cycles += 1;
          trades.push({
            type: "put_expired",
            date: row.date,
            qty: wheelPosition.qty,
            strike: wheelPosition.strike,
            premium: wheelPosition.premium,
          });
          wheelPosition = null;
        } else {
          assignedCount += 1;
          const sharesBought = wheelPosition.qty * CONFIG.tqqqOption.contractMultiplier;
          cash -= wheelPosition.strike * sharesBought;
          shares += sharesBought;
          shareCostBasis = wheelPosition.strike - wheelPosition.premium / CONFIG.tqqqOption.contractMultiplier;
          trades.push({
            type: "put_assigned",
            date: row.date,
            qty: wheelPosition.qty,
            strike: wheelPosition.strike,
            costBasis: shareCostBasis,
          });
          const originalPutStrike = wheelPosition.strike;
          wheelPosition = null;

          if (row.qqqClose <= row.qqqSma200) {
            cash += shares * row.tqqqClose;
            trades.push({
              type: "assignment_stop_loss",
              date: row.date,
              qty: shares / CONFIG.tqqqOption.contractMultiplier,
              price: row.tqqqClose,
            });
            shares = 0;
            shareCostBasis = 0;
            stopLosses += 1;
            cycles += 1;
          } else {
            const strike = roundTo(originalPutStrike, CONFIG.tqqqOption.roundStrikeTo);
            const premium = callPrice(
              row.tqqqClose,
              strike,
              CONFIG.tqqqOption.dteDays / 365.25,
              CONFIG.tqqqOption.riskFreeRate,
              row.tqqqIv || CONFIG.tqqqOption.minIv,
            ) * CONFIG.tqqqOption.contractMultiplier * (shares / CONFIG.tqqqOption.contractMultiplier);
            cash += premium;
            wheelPosition = {
              kind: "short_call",
              entryDate: row.date,
              expiryDate: addUtcDays(row.date, CONFIG.tqqqOption.dteDays),
              strike,
              premium,
              qty: shares / CONFIG.tqqqOption.contractMultiplier,
            };
            trades.push({
              type: "sell_call",
              date: row.date,
              qty: wheelPosition.qty,
              strike,
              premium,
            });
          }
        }
      } else if (wheelPosition.kind === "short_call") {
        if (row.tqqqClose >= wheelPosition.strike) {
          cash += shares * wheelPosition.strike;
          trades.push({
            type: "shares_called_away",
            date: row.date,
            qty: wheelPosition.qty,
            strike: wheelPosition.strike,
          });
          shares = 0;
          shareCostBasis = 0;
          wheelPosition = null;
          cycles += 1;
        } else {
          const qty = shares / CONFIG.tqqqOption.contractMultiplier;
          const strike = wheelPosition.strike;
          const premium = callPrice(
            row.tqqqClose,
            strike,
            CONFIG.tqqqOption.dteDays / 365.25,
            CONFIG.tqqqOption.riskFreeRate,
            row.tqqqIv || CONFIG.tqqqOption.minIv,
          ) * CONFIG.tqqqOption.contractMultiplier * qty;
          cash += premium;
          shareCostBasis -= premium / Math.max(shares, 1);
          wheelPosition = {
            kind: "short_call",
            entryDate: row.date,
            expiryDate: addUtcDays(row.date, CONFIG.tqqqOption.dteDays),
            strike,
            premium,
            qty,
          };
          trades.push({
            type: "roll_call",
            date: row.date,
            qty,
            strike,
            premium,
            revisedCostBasis: shareCostBasis,
          });
        }
      }
    }

    if (!wheelPosition && shares === 0 && signalAllowsShortPut(row)) {
      const strike = roundTo(row.tqqqClose * CONFIG.tqqqOption.putStrikePct, CONFIG.tqqqOption.roundStrikeTo);
      const requiredCash = strike * CONFIG.tqqqOption.contractMultiplier;
      if (cash >= requiredCash) {
        const premium = putPrice(
          row.tqqqClose,
          strike,
          CONFIG.tqqqOption.dteDays / 365.25,
          CONFIG.tqqqOption.riskFreeRate,
          row.tqqqIv || CONFIG.tqqqOption.minIv,
        ) * CONFIG.tqqqOption.contractMultiplier;
        cash += premium;
        wheelPosition = {
          kind: "short_put",
          entryDate: row.date,
          expiryDate: addUtcDays(row.date, CONFIG.tqqqOption.dteDays),
          strike,
          premium,
          qty: 1,
        };
        trades.push({
          type: "sell_put",
          date: row.date,
          qty: 1,
          strike,
          premium,
        });
      }
    }

    const equity = cash + shares * row.tqqqClose + (wheelPosition ? priceShortWheelOption(row, wheelPosition) : 0);
    equityCurve.push({ date: row.date, equity });
    if (!reachedDate && equity >= CONFIG.stage1.stopAtEquity) {
      reachedDate = row.date;
    }
  }

  const endingEquity = equityCurve.at(-1).equity;
  cashflows.push({ date: equityCurve.at(-1).date, amount: endingEquity });
  const maxDrawdown = maxDrawdownFromSeries(equityCurve);
  const reachIndex = reachedDate ? equityCurve.findIndex((point) => point.date === reachedDate) : -1;
  const daysToTarget = reachIndex >= 0 ? dayDiff(CONFIG.start, reachedDate) : null;
  const contributedAtTarget = reachedDate
    ? -cashflows.filter((flow) => flow.date <= reachedDate && flow.amount < 0).reduce((sum, flow) => sum + flow.amount, 0)
    : null;
  const equityAtTarget = reachIndex >= 0 ? equityCurve[reachIndex].equity : null;

  return {
    trades,
    equityCurve,
    summary: {
      model: "Stage 1 wheel-only approximation from the video",
      startCapital: CONFIG.stage1.initialCapital,
      monthlyContribution: CONFIG.monthlyContribution,
      targetEquity: CONFIG.stage1.stopAtEquity,
      reachedTarget: Boolean(reachedDate),
      reachedTargetDate: reachedDate,
      daysToTarget,
      contributedAtTarget,
      equityAtTarget,
      excessOverContributionsAtTarget: reachedDate && contributedAtTarget != null && equityAtTarget != null
        ? equityAtTarget - contributedAtTarget
        : null,
      endingEquity,
      totalContributed: CONFIG.stage1.initialCapital + (new Set(equityCurve.map((point) => monthKey(point.date))).size - 1) * CONFIG.monthlyContribution,
      completedCycles: cycles,
      assignedCount,
      stopLosses,
      maxDrawdown,
      moneyWeightedReturn: xirr(cashflows),
      assumptions: {
        signal: "QQQ > SMA200, RSI(14) < 50, and QQQ closes down on the day",
        wheel: "~33 calendar DTE cash-secured put on TQQQ, one contract max",
        putStrike: "8% OTM, rounded to nearest $1",
        coveredCall: "after bullish assignment, sell 33 DTE covered call at original put strike",
        bearRule: "if assigned while QQQ is at or below SMA200, exit the TQQQ shares immediately",
      },
    },
  };
}

function createLeapsPosition(row, capital) {
  const t = CONFIG.leaps.dteDays / 365.25;
  const sigma = row.qqqIv || CONFIG.leaps.minIv;
  const strike = strikeForTargetCallDelta(
    row.qqqNominalClose,
    CONFIG.leaps.targetDelta,
    t,
    CONFIG.leaps.riskFreeRate,
    sigma,
    CONFIG.leaps.roundStrikeTo,
  );
  const optionValue = callPrice(row.qqqNominalClose, strike, t, CONFIG.leaps.riskFreeRate, sigma) * CONFIG.leaps.contractMultiplier;
  const qty = optionValue > 0 ? capital / optionValue : 0;
  return {
    entryDate: row.date,
    expiryDate: addUtcDays(row.date, CONFIG.leaps.dteDays),
    strike,
    qty,
    entryValue: capital,
  };
}

function runStage2(rows) {
  const basePct = Math.min(0.8, (CONFIG.stage2.age + 20) / 100);
  const cashPct = CONFIG.stage2.cashPct;
  const wheelPct = CONFIG.stage2.wheelPct;
  const leapsPct = CONFIG.stage2.leapsPct;

  let coreShares = 0;
  let cashSleeve = CONFIG.stage2.initialCapital * cashPct;
  let wheelCash = CONFIG.stage2.initialCapital * wheelPct;
  let wheelShares = 0;
  let wheelShareCostBasis = 0;
  let wheelPosition = null;
  let leapsPosition = null;
  let currentMonth = null;
  let completedCycles = 0;
  let stopLosses = 0;
  const tradeLog = [];
  const equityCurve = [];
  const cashflows = [{ date: rows[0].date, amount: -CONFIG.stage2.initialCapital }];

  const firstRow = rows.find((row) => Number.isFinite(row.qqqSma200) && Number.isFinite(row.qqqRsi14) && Number.isFinite(row.qqqIv));
  coreShares = (CONFIG.stage2.initialCapital * basePct) / firstRow.qqqClose;
  leapsPosition = createLeapsPosition(firstRow, CONFIG.stage2.initialCapital * leapsPct);

  for (const row of rows) {
    if (row.date < firstRow.date) continue;

    if (currentMonth !== monthKey(row.date)) {
      currentMonth = monthKey(row.date);
      if (row.date > firstRow.date) {
        const contribution = CONFIG.monthlyContribution;
        cashflows.push({ date: row.date, amount: -contribution });
        coreShares += (contribution * basePct) / row.qqqClose;
        cashSleeve += contribution * cashPct;
        wheelCash += contribution * wheelPct;
        const leapsCapital = contribution * leapsPct;
        if (leapsPosition) {
          const existingValue = priceLeapsOption(row, leapsPosition);
          const targetValue = existingValue + leapsCapital;
          leapsPosition = createLeapsPosition(row, targetValue);
        } else {
          leapsPosition = createLeapsPosition(row, leapsCapital);
        }
      }
    }

    if (leapsPosition && optionDaysLeft(row.date, leapsPosition.expiryDate) <= CONFIG.leaps.rollWhenDaysLeft) {
      const currentValue = priceLeapsOption(row, leapsPosition);
      leapsPosition = createLeapsPosition(row, currentValue);
      tradeLog.push({
        type: "roll_leaps",
        date: row.date,
        value: currentValue,
        strike: leapsPosition.strike,
      });
    }

    if (wheelPosition && row.date >= wheelPosition.expiryDate) {
      if (wheelPosition.kind === "short_put") {
        if (row.tqqqClose >= wheelPosition.strike) {
          tradeLog.push({
            type: "stage2_put_expired",
            date: row.date,
            qty: wheelPosition.qty,
            strike: wheelPosition.strike,
          });
          wheelPosition = null;
          completedCycles += 1;
        } else {
          const sharesBought = wheelPosition.qty * CONFIG.tqqqOption.contractMultiplier;
          wheelCash -= wheelPosition.strike * sharesBought;
          wheelShares += sharesBought;
          wheelShareCostBasis = wheelPosition.strike - wheelPosition.premiumPerContract / CONFIG.tqqqOption.contractMultiplier;
          const assignedStrike = wheelPosition.strike;
          wheelPosition = null;

          if (row.qqqClose <= row.qqqSma200) {
            wheelCash += wheelShares * row.tqqqClose;
            wheelShares = 0;
            wheelShareCostBasis = 0;
            stopLosses += 1;
            completedCycles += 1;
            tradeLog.push({
              type: "stage2_stop_loss",
              date: row.date,
              price: row.tqqqClose,
            });
          } else {
            const qty = sharesBought / CONFIG.tqqqOption.contractMultiplier;
            const premiumPerContract = callPrice(
              row.tqqqClose,
              assignedStrike,
              CONFIG.tqqqOption.dteDays / 365.25,
              CONFIG.tqqqOption.riskFreeRate,
              row.tqqqIv || CONFIG.tqqqOption.minIv,
            ) * CONFIG.tqqqOption.contractMultiplier;
            wheelCash += premiumPerContract * qty;
            wheelPosition = {
              kind: "short_call",
              entryDate: row.date,
              expiryDate: addUtcDays(row.date, CONFIG.tqqqOption.dteDays),
              strike: assignedStrike,
              premiumPerContract,
              qty,
            };
            tradeLog.push({
              type: "stage2_sell_call",
              date: row.date,
              qty,
              strike: assignedStrike,
              premiumPerContract,
            });
          }
        }
      } else if (wheelPosition.kind === "short_call") {
        if (row.tqqqClose >= wheelPosition.strike) {
          const calledAwayStrike = wheelPosition.strike;
          wheelCash += wheelShares * wheelPosition.strike;
          wheelShares = 0;
          wheelShareCostBasis = 0;
          wheelPosition = null;
          completedCycles += 1;
          tradeLog.push({
            type: "stage2_called_away",
            date: row.date,
            strike: calledAwayStrike,
          });
        } else {
          const qty = wheelShares / CONFIG.tqqqOption.contractMultiplier;
          const strike = wheelPosition.strike;
          const premiumPerContract = callPrice(
            row.tqqqClose,
            strike,
            CONFIG.tqqqOption.dteDays / 365.25,
            CONFIG.tqqqOption.riskFreeRate,
            row.tqqqIv || CONFIG.tqqqOption.minIv,
          ) * CONFIG.tqqqOption.contractMultiplier;
          wheelCash += premiumPerContract * qty;
          wheelShareCostBasis -= premiumPerContract / CONFIG.tqqqOption.contractMultiplier;
          wheelPosition = {
            kind: "short_call",
            entryDate: row.date,
            expiryDate: addUtcDays(row.date, CONFIG.tqqqOption.dteDays),
            strike,
            premiumPerContract,
            qty,
          };
          tradeLog.push({
            type: "stage2_roll_call",
            date: row.date,
            qty,
            strike,
            premiumPerContract,
          });
        }
      }
    }

    if (!wheelPosition && wheelShares === 0 && signalAllowsShortPut(row)) {
      const strike = roundTo(row.tqqqClose * CONFIG.tqqqOption.putStrikePct, CONFIG.tqqqOption.roundStrikeTo);
      const collateralPerContract = strike * CONFIG.tqqqOption.contractMultiplier;
      const qty = wheelCash > 0 ? wheelCash / collateralPerContract : 0;
      if (qty >= 0.25) {
        const premiumPerContract = putPrice(
          row.tqqqClose,
          strike,
          CONFIG.tqqqOption.dteDays / 365.25,
          CONFIG.tqqqOption.riskFreeRate,
          row.tqqqIv || CONFIG.tqqqOption.minIv,
        ) * CONFIG.tqqqOption.contractMultiplier;
        wheelCash += premiumPerContract * qty;
        wheelPosition = {
          kind: "short_put",
          entryDate: row.date,
          expiryDate: addUtcDays(row.date, CONFIG.tqqqOption.dteDays),
          strike,
          premiumPerContract,
          qty,
        };
        tradeLog.push({
          type: "stage2_sell_put",
          date: row.date,
          qty,
          strike,
          premiumPerContract,
        });
      }
    }

    const coreValue = coreShares * row.qqqClose;
    const wheelValue = wheelCash + wheelShares * row.tqqqClose + (wheelPosition ? priceShortWheelOption(row, wheelPosition) : 0);
    const leapsValue = leapsPosition ? priceLeapsOption(row, leapsPosition) : 0;
    const equity = coreValue + cashSleeve + wheelValue + leapsValue;
    equityCurve.push({
      date: row.date,
      equity,
      coreValue,
      cashValue: cashSleeve,
      wheelValue,
      leapsValue,
    });
  }

  const startDate = equityCurve[0].date;
  const endDate = equityCurve.at(-1).date;
  const endingEquity = equityCurve.at(-1).equity;
  cashflows.push({ date: endDate, amount: endingEquity });
  const totalContributed = CONFIG.stage2.initialCapital + (new Set(equityCurve.map((point) => monthKey(point.date))).size - 1) * CONFIG.monthlyContribution;

  return {
    tradeLog,
    equityCurve,
    summary: {
      model: "Stage 2 approximate allocation model from the video",
      ageAssumption: CONFIG.stage2.age,
      startCapital: CONFIG.stage2.initialCapital,
      monthlyContribution: CONFIG.monthlyContribution,
      allocation: {
        coreQqqProxy: basePct,
        cashReserve: cashPct,
        tqqqWheel: wheelPct,
        qqqLeaps: leapsPct,
      },
      qqqmProxy: "QQQ adjusted close used as long-history proxy for QQQM",
      endingEquity,
      totalContributed,
      multipleOnContributedCapital: endingEquity / totalContributed,
      moneyWeightedReturn: xirr(cashflows),
      maxDrawdown: maxDrawdownFromSeries(equityCurve),
      completedWheelCycles: completedCycles,
      wheelStopLosses: stopLosses,
      assumptions: {
        wheelSignal: "QQQ > SMA200, RSI(14) < 50, and QQQ closes down on the day",
        wheelSizing: "fractional contract sizing used as portfolio-level approximation",
        leaps: "continuous deep-ITM (~delta 0.8) 2Y QQQ LEAPS call, rolled when 1Y remains",
        reallocation: "new monthly contributions split by target weights; no full monthly rebalance",
      },
    },
  };
}

function csvEscape(value) {
  if (value == null) return "";
  const s = typeof value === "number" ? String(value) : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function writeCsv(file, rows) {
  if (!rows.length) {
    fs.writeFileSync(file, "");
    return;
  }
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map((header) => csvEscape(row[header])).join(","));
  }
  fs.writeFileSync(file, `${lines.join("\n")}\n`);
}

async function main() {
  const [qqqRows, tqqqRows] = await Promise.all([
    fetchYahooChart("QQQ", addUtcDays(CONFIG.start, -500), CONFIG.end),
    fetchYahooChart("TQQQ", addUtcDays(CONFIG.start, -500), CONFIG.end),
  ]);

  computeSma(qqqRows, CONFIG.qqqSignal.smaPeriod, "close", "qqqSma200");
  computeRsi(qqqRows, CONFIG.qqqSignal.rsiPeriod, "close", "qqqRsi14");
  computeRealizedIv(qqqRows, CONFIG.leaps.ivLookbackDays, CONFIG.leaps.ivMultiplier, CONFIG.leaps.minIv, CONFIG.leaps.maxIv, "qqqIv", "close");
  computeRealizedIv(tqqqRows, CONFIG.tqqqOption.ivLookbackDays, CONFIG.tqqqOption.ivMultiplier, CONFIG.tqqqOption.minIv, CONFIG.tqqqOption.maxIv, "tqqqIv", "close");

  const rows = buildMarketRows(qqqRows, tqqqRows);
  const stage1 = runStage1(rows);
  const stage2 = runStage2(rows);

  fs.mkdirSync(CONFIG.outputDir, { recursive: true });
  fs.writeFileSync(path.join(CONFIG.outputDir, "stage1_summary.json"), JSON.stringify(stage1.summary, null, 2));
  fs.writeFileSync(path.join(CONFIG.outputDir, "stage2_summary.json"), JSON.stringify(stage2.summary, null, 2));
  writeCsv(path.join(CONFIG.outputDir, "stage1_equity_curve.csv"), stage1.equityCurve);
  writeCsv(path.join(CONFIG.outputDir, "stage1_trades.csv"), stage1.trades);
  writeCsv(path.join(CONFIG.outputDir, "stage2_equity_curve.csv"), stage2.equityCurve);
  writeCsv(path.join(CONFIG.outputDir, "stage2_trades.csv"), stage2.tradeLog);

  console.log(JSON.stringify({ stage1: stage1.summary, stage2: stage2.summary }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message);
  process.exit(1);
});
