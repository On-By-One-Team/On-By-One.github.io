let rawData = null;
let currentMode = "all"; // "all" | "week" | "sprint" | "block"
let hoursGaugeChart = null;
let costGaugeChart = null;
let roleChart = null;
let memberChart = null;
let weekChart = null;

// Ordine fisso dei componenti del gruppo (per cognome)
const MEMBER_ORDER = [
    "Sara Ballardin",
    "Shuhui Chen",
    "Simone Giuliano",
    "Alvise Greggio",
    "Daniele Nuzzaci",
    "Federico Temporin",
    "Tommaso Zorzetto"
];

// Plugin Chart.js per disegnare la lancetta a tachimetro sul grafico a semicerchio
const gaugeNeedlePlugin = {
    id: "gaugeNeedle",
    afterDatasetDraw(chart) {
        const cfg = chart.config.options.plugins && chart.config.options.plugins.gaugeNeedle;
        if (!cfg || typeof cfg.percentage !== "number") return;

        const meta = chart.getDatasetMeta(0);
        if (!meta || !meta.data || !meta.data.length) return;

        const arc = meta.data[0];
        const cx = arc.x;
        const cy = arc.y;
        const outerRadius = arc.outerRadius;
        const innerRadius = arc.innerRadius;

        const clamped = Math.max(0, Math.min(100, cfg.percentage));
        const angle = Math.PI + (clamped / 100) * Math.PI;
        const needleLen = innerRadius + (outerRadius - innerRadius) * 0.78;
        const baseWidth = 5;

        const { ctx } = chart;
        ctx.save();

        ctx.translate(cx, cy);
        ctx.rotate(angle);
        ctx.beginPath();
        ctx.moveTo(0, -baseWidth);
        ctx.lineTo(needleLen, 0);
        ctx.lineTo(0, baseWidth);
        ctx.closePath();
        ctx.fillStyle = "#1e293b";
        ctx.fill();

        ctx.beginPath();
        ctx.arc(0, 0, 7, 0, Math.PI * 2);
        ctx.fillStyle = "#1e293b";
        ctx.fill();
        ctx.beginPath();
        ctx.arc(0, 0, 3, 0, Math.PI * 2);
        ctx.fillStyle = "#ffffff";
        ctx.fill();

        ctx.restore();

        ctx.save();
        ctx.font = "600 11px system-ui, -apple-system, sans-serif";
        ctx.fillStyle = "#64748b";
        ctx.textAlign = "center";
        ctx.fillText("0%", cx - outerRadius + 10, cy + 14);
        ctx.fillText("100%", cx + outerRadius - 12, cy + 14);
        ctx.restore();
    }
};

const plannedHoursForWeek = (roleCfg, weekNum) => {
    if (!weekNum || weekNum < 1) return 0;
    const blockIdx = Math.min(Math.floor((weekNum - 1) / 4), roleCfg.weekly_plan_by_block.length - 1);
    return roleCfg.weekly_plan_by_block[blockIdx];
};

const parseSprintNum = (sprintStr) => {
    const match = sprintStr && sprintStr.match(/\d+/);
    return match ? parseInt(match[0], 10) : 0;
};

const sprintLabelForWeek = (entries, weekNum) => {
    const sprints = [...new Set(
        entries
            .filter((e) => e.week_number === weekNum && e.sprint)
            .map((e) => e.sprint)
    )].sort((a, b) => parseSprintNum(a) - parseSprintNum(b));
    return sprints.join(" / ");
};

// Mappa ogni settimana allo sprint prevalente, cosi' le Draft Issue senza label rientrano nel loro sprint
const buildWeekPrimarySprintMap = (entries) => {
    const countsByWeek = {};
    entries.forEach((e) => {
        if (!e.week_number || !e.sprint) return;
        if (!countsByWeek[e.week_number]) countsByWeek[e.week_number] = {};
        countsByWeek[e.week_number][e.sprint] = (countsByWeek[e.week_number][e.sprint] || 0) + 1;
    });

    const primary = {};
    Object.entries(countsByWeek).forEach(([wn, counts]) => {
        const sorted = Object.entries(counts).sort(
            (a, b) => b[1] - a[1] || parseSprintNum(b[0]) - parseSprintNum(a[0])
        );
        primary[wn] = sorted[0][0];
    });
    return primary;
};

const resolveEntrySprint = (entry, weekPrimarySprint) =>
    entry.sprint || weekPrimarySprint[entry.week_number] || "";

const blockWeekRange = (blockNum, projectWeeks) => {
    const start = (blockNum - 1) * 4 + 1;
    const end = Math.min(blockNum * 4, projectWeeks);
    return { start, end };
};

const weeksInRange = (start, end) =>
    Array.from({ length: Math.max(0, end - start + 1) }, (_, i) => start + i);

const orderedMembers = (membersObj, entries) => {
    const set = new Set([
        ...MEMBER_ORDER,
        ...Object.values(membersObj || {}),
        ...entries.map((e) => e.member_name)
    ]);
    return [...set].sort((a, b) => {
        const ia = MEMBER_ORDER.indexOf(a);
        const ib = MEMBER_ORDER.indexOf(b);
        if (ia !== -1 && ib !== -1) return ia - ib;
        if (ia !== -1) return -1;
        if (ib !== -1) return 1;
        return a.localeCompare(b, "it");
    });
};

const gaugeColorForPct = (pct) => {
    if (pct > 100) return "#dc2626";
    if (pct >= 85) return "#d97706";
    return "#5d3a9b";
};

const buildGauge = (canvasId, prevInstance, pct) => {
    if (prevInstance) prevInstance.destroy();
    const clamped = Math.max(0, Math.min(100, pct));
    const fillColor = gaugeColorForPct(pct);

    return new Chart(document.getElementById(canvasId), {
        type: "doughnut",
        data: {
            datasets: [
                {
                    data: [clamped, 100 - clamped],
                    backgroundColor: [fillColor, "#e2e8f0"],
                    borderWidth: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            rotation: -90,
            circumference: 180,
            cutout: "70%",
            layout: { padding: { top: 6, bottom: 18, left: 10, right: 10 } },
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
                gaugeNeedle: { percentage: pct }
            }
        },
        plugins: [gaugeNeedlePlugin]
    });
};

const getValidEntries = () => {
    const { roles } = rawData.budget;
    return rawData.entries.filter((e) => roles[e.role] && e.week_number >= 1);
};

const populatePeriodSelect = () => {
    const wrap = document.getElementById("period-select-wrap");
    const labelEl = document.getElementById("period-select-label");
    const selectEl = document.getElementById("period-select");

    if (currentMode === "all") {
        wrap.hidden = true;
        selectEl.innerHTML = "";
        return;
    }

    wrap.hidden = false;
    const validEntries = getValidEntries();
    const weekPrimarySprint = buildWeekPrimarySprintMap(validEntries);
    const projectWeeks = rawData.budget.project_weeks || 20;

    if (currentMode === "week") {
        labelEl.textContent = "Settimana";
        const weekNums = [...new Set(validEntries.map((e) => e.week_number))].sort((a, b) => a - b);
        if (!weekNums.length) {
            selectEl.innerHTML = `<option value="">Nessuna settimana attiva</option>`;
            return;
        }
        selectEl.innerHTML = weekNums.map((wn) => {
            const sp = sprintLabelForWeek(validEntries, wn);
            const txt = sp ? `Settimana ${wn} (${sp})` : `Settimana ${wn}`;
            return `<option value="${wn}">${txt}</option>`;
        }).join("");
        selectEl.value = String(weekNums[weekNums.length - 1]);
        return;
    }

    if (currentMode === "sprint") {
        labelEl.textContent = "Sprint";
        const sprints = [...new Set(
            validEntries.map((e) => resolveEntrySprint(e, weekPrimarySprint)).filter(Boolean)
        )].sort((a, b) => parseSprintNum(a) - parseSprintNum(b));

        if (!sprints.length) {
            selectEl.innerHTML = `<option value="">Nessuno sprint rilevato</option>`;
            return;
        }
        selectEl.innerHTML = sprints.map((sp) => {
            const wks = [...new Set(
                validEntries
                    .filter((e) => resolveEntrySprint(e, weekPrimarySprint) === sp)
                    .map((e) => e.week_number)
            )].sort((a, b) => a - b);
            const wkTxt = wks.length === 1
                ? `Sett. ${wks[0]}`
                : `Sett. ${wks[0]}–${wks[wks.length - 1]}`;
            return `<option value="${sp}">${sp} (${wkTxt})</option>`;
        }).join("");
        selectEl.value = sprints[sprints.length - 1];
        return;
    }

    if (currentMode === "block") {
        labelEl.textContent = "Blocco";
        const totalBlocks = Math.ceil(projectWeeks / 4);
        const lastLoggedWeek = Math.max(0, ...validEntries.map((e) => e.week_number || 0));
        const activeBlock = lastLoggedWeek > 0
            ? Math.min(Math.ceil(lastLoggedWeek / 4), totalBlocks)
            : 1;

        selectEl.innerHTML = Array.from({ length: totalBlocks }, (_, idx) => {
            const bNum = idx + 1;
            const { start, end } = blockWeekRange(bNum, projectWeeks);
            return `<option value="${bNum}">Blocco ${bNum} (Sett. ${start}–${end})</option>`;
        }).join("");
        selectEl.value = String(activeBlock);
    }
};

const render = () => {
    const {
        roles,
        project_weeks: projectWeeks = 20,
        target_hours_per_member: targetMember = 88,
        max_hours_per_member: maxMember = 95,
        total_budget_eur: totalBudget
    } = rawData.budget;
    const roleKeys = Object.keys(roles);
    const validEntries = getValidEntries();
    const weekPrimarySprint = buildWeekPrimarySprintMap(validEntries);
    const selectVal = document.getElementById("period-select").value;

    const isFullProject = currentMode === "all";
    const selectedWeekNum = currentMode === "week" && selectVal ? parseInt(selectVal, 10) : null;
    const selectedSprint = currentMode === "sprint" && selectVal ? selectVal : null;
    const selectedBlockNum = currentMode === "block" && selectVal ? parseInt(selectVal, 10) : null;

    // Filtraggio esclusivo in base alla modalita' selezionata
    let filtered = validEntries;
    let plannedWeeks = [];
    let periodDesc = `intero progetto (${projectWeeks} settimane)`;
    let hintText = "";

    if (isFullProject) {
        const allSprints = [...new Set(validEntries.map((e) => e.sprint).filter(Boolean))]
            .sort((a, b) => parseSprintNum(a) - parseSprintNum(b));
        const latestSprint = allSprints[allSprints.length - 1];
        hintText = latestSprint
            ? `Ultimo sprint attivo: ${latestSprint} (${allSprints.length} registrati)`
            : "";
    } else if (currentMode === "week" && selectedWeekNum) {
        filtered = validEntries.filter((e) => e.week_number === selectedWeekNum);
        plannedWeeks = [selectedWeekNum];
        periodDesc = `la Settimana ${selectedWeekNum}`;
        const bNum = Math.ceil(selectedWeekNum / 4);
        const sp = sprintLabelForWeek(validEntries, selectedWeekNum);
        hintText = sp ? `Blocco ${bNum} · ${sp}` : `Blocco ${bNum}`;
    } else if (currentMode === "sprint" && selectedSprint) {
        filtered = validEntries.filter((e) => resolveEntrySprint(e, weekPrimarySprint) === selectedSprint);
        plannedWeeks = [...new Set(filtered.map((e) => e.week_number))].sort((a, b) => a - b);
        periodDesc = selectedSprint;
        hintText = plannedWeeks.length
            ? `Settimane coperte: ${plannedWeeks.map((w) => `S${w}`).join(", ")}`
            : "Nessuna settimana associata";
    } else if (currentMode === "block" && selectedBlockNum) {
        const { start, end } = blockWeekRange(selectedBlockNum, projectWeeks);
        filtered = validEntries.filter((e) => e.week_number >= start && e.week_number <= end);
        plannedWeeks = weeksInRange(start, end);
        periodDesc = `il Blocco ${selectedBlockNum} (Sett. ${start}–${end})`;
        const blockSprints = [...new Set(
            filtered.map((e) => resolveEntrySprint(e, weekPrimarySprint)).filter(Boolean)
        )].sort((a, b) => parseSprintNum(a) - parseSprintNum(b));
        hintText = blockSprints.length
            ? `Sprint inclusi: ${blockSprints.join(", ")}`
            : `Settimane ${start}–${end} (nessuna ora rendicontata)`;
    } else {
        filtered = [];
        plannedWeeks = [];
    }

    document.getElementById("filter-sprint-info").textContent = hintText;

    // Preventivo per ruolo nel periodo scelto
    const plannedByRole = {};
    roleKeys.forEach((rk) => {
        plannedByRole[rk] = isFullProject
            ? roles[rk].total_hours
            : plannedWeeks.reduce((sum, wn) => sum + plannedHoursForWeek(roles[rk], wn), 0);
    });

    // Consuntivo per ruolo
    const actualByRole = {};
    roleKeys.forEach((rk) => {
        actualByRole[rk] = 0;
    });
    filtered.forEach((e) => {
        actualByRole[e.role] += e.hours;
    });

    const totalPlannedHours = Object.values(plannedByRole).reduce((a, b) => a + b, 0);
    const totalActualHours = filtered.reduce((a, e) => a + e.hours, 0);
    const totalActualCost = roleKeys.reduce((acc, rk) => acc + actualByRole[rk] * roles[rk].hourly_rate, 0);
    const periodBudgetEur = isFullProject
        ? totalBudget
        : roleKeys.reduce((acc, rk) => acc + plannedByRole[rk] * roles[rk].hourly_rate, 0);

    const hoursPct = totalPlannedHours > 0 ? (totalActualHours / totalPlannedHours) * 100 : 0;
    const costPct = periodBudgetEur > 0 ? (totalActualCost / periodBudgetEur) * 100 : 0;

    // 1. Tachimetri Ore e Budget
    hoursGaugeChart = buildGauge("hoursGauge", hoursGaugeChart, hoursPct);
    const hoursPctEl = document.getElementById("gauge-hours-pct");
    hoursPctEl.textContent = `${hoursPct.toFixed(1)}%`;
    hoursPctEl.style.color = gaugeColorForPct(hoursPct);
    document.getElementById("gauge-hours-sub").textContent =
        `${totalActualHours.toFixed(1)} h fatte su ${totalPlannedHours.toFixed(0)} h preventivate`;

    costGaugeChart = buildGauge("costGauge", costGaugeChart, costPct);
    const costPctEl = document.getElementById("gauge-cost-pct");
    costPctEl.textContent = `${costPct.toFixed(1)}%`;
    costPctEl.style.color = gaugeColorForPct(costPct);
    document.getElementById("gauge-cost-sub").textContent =
        `€ ${totalActualCost.toFixed(0)} spesi su € ${periodBudgetEur.toFixed(0)} preventivati`;

    // 2. Scheda Ore Medie a Settimana
    const activeWeekNums = [...new Set(filtered.map((e) => e.week_number))];
    const weeksCount = activeWeekNums.length;
    const avgWeeklyHours = weeksCount > 0 ? totalActualHours / weeksCount : 0;
    const plannedActiveWeeks = activeWeekNums.reduce(
        (sum, wn) => sum + roleKeys.reduce((rSum, rk) => rSum + plannedHoursForWeek(roles[rk], wn), 0),
        0
    );
    const avgPlannedWeekly = weeksCount > 0 ? plannedActiveWeeks / weeksCount : 0;
    const allMembers = orderedMembers(rawData.members, validEntries);
    const memberCount = allMembers.length || 7;
    const remainingHours = totalPlannedHours - totalActualHours;

    document.getElementById("kpi-weekly-avg").textContent = `${avgWeeklyHours.toFixed(1)} h/sett`;
    document.getElementById("kpi-weekly-sub").textContent = weeksCount > 0
        ? `Su ${weeksCount} ${weeksCount === 1 ? "settimana" : "settimane"} attive (preventivo medio: ${avgPlannedWeekly.toFixed(1)} h/sett)`
        : "Nessuna settimana rendicontata nel periodo";
    document.getElementById("kpi-member-avg").textContent = `${(totalActualHours / memberCount).toFixed(1)} h`;
    document.getElementById("kpi-member-target").textContent = `${targetMember} h / ${maxMember} h`;
    document.getElementById("kpi-hours-remaining").textContent = `${remainingHours.toFixed(1)} h`;

    // 3. Grafico Preventivo vs Consuntivo per Ruolo
    document.getElementById("role-chart-desc").textContent = `Confronto ore per ${periodDesc}`;

    if (roleChart) roleChart.destroy();
    roleChart = new Chart(document.getElementById("roleChart"), {
        type: "bar",
        data: {
            labels: roleKeys.map((rk) => roles[rk].label),
            datasets: [
                {
                    label: "Preventivo (h)",
                    data: roleKeys.map((rk) => plannedByRole[rk]),
                    backgroundColor: "rgba(93, 58, 155, 0.22)",
                    borderColor: "#5d3a9b",
                    borderWidth: 1.5
                },
                {
                    label: "Consuntivo (h)",
                    data: roleKeys.map((rk) => Number(actualByRole[rk].toFixed(2))),
                    backgroundColor: "#5d3a9b"
                }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
    });

    // 4. Grafico Carico per Singolo Membro
    const memberTotals = allMembers.map((m) =>
        Number(
            filtered
                .filter((e) => e.member_name === m)
                .reduce((s, e) => s + e.hours, 0)
                .toFixed(2)
        )
    );

    const memberBarColors = memberTotals.map((h) => {
        if (!isFullProject) return "#5d3a9b";
        if (h > maxMember) return "#dc2626";
        if (h > targetMember) return "#d97706";
        return "#5d3a9b";
    });

    document.getElementById("member-chart-desc").textContent = isFullProject
        ? `Ore totali per persona rispetto al target (${targetMember} h) e al limite massimo (${maxMember} h)`
        : `Ore svolte da ciascun componente in ${periodDesc}`;

    const memberDatasets = [
        {
            type: "bar",
            label: "Ore svolte (h)",
            data: memberTotals,
            backgroundColor: memberBarColors,
            order: 2
        }
    ];

    if (isFullProject) {
        memberDatasets.push(
            {
                type: "line",
                label: `Target (${targetMember} h)`,
                data: allMembers.map(() => targetMember),
                borderColor: "#d97706",
                backgroundColor: "#d97706",
                borderDash: [6, 4],
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 0,
                pointHitRadius: 0,
                order: 1
            },
            {
                type: "line",
                label: `Limite max (${maxMember} h)`,
                data: allMembers.map(() => maxMember),
                borderColor: "#dc2626",
                backgroundColor: "#dc2626",
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 0,
                pointHitRadius: 0,
                order: 1
            }
        );
    }

    if (memberChart) memberChart.destroy();
    memberChart = new Chart(document.getElementById("memberChart"), {
        type: "bar",
        data: { labels: allMembers, datasets: memberDatasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: isFullProject ? Math.max(100, maxMember + 5) : undefined
                }
            }
        }
    });

    // 5. Grafico Andamento Temporale (adattato alla modalita' scelta)
    const trendTitleEl = document.getElementById("trend-chart-title");
    const trendDescEl = document.getElementById("trend-chart-desc");
    const lastLoggedWeek = Math.max(0, ...validEntries.map((e) => e.week_number || 0));

    let trendLabels = [];
    let trendActuals = [];
    let trendPlans = [];
    let trendColors = [];
    let planSeriesLabel = "Preventivo (h)";

    if (currentMode === "block") {
        trendTitleEl.textContent = "Consuntivo vs Preventivo per Blocco (4 settimane)";
        trendDescEl.textContent = "Confronto sui 5 blocchi pianificati con evidenza sul blocco selezionato";
        planSeriesLabel = "Preventivo blocco (h)";

        const totalBlocks = Math.ceil(projectWeeks / 4);
        for (let b = 1; b <= totalBlocks; b += 1) {
            const { start, end } = blockWeekRange(b, projectWeeks);
            trendLabels.push([`Blocco ${b}`, `S${start}–S${end}`]);

            const planned = weeksInRange(start, end).reduce(
                (acc, wn) => acc + roleKeys.reduce((rSum, rk) => rSum + plannedHoursForWeek(roles[rk], wn), 0),
                0
            );
            trendPlans.push(planned);

            if (start > lastLoggedWeek) {
                trendActuals.push(null);
            } else {
                const actual = validEntries
                    .filter((e) => e.week_number >= start && e.week_number <= end)
                    .reduce((s, e) => s + e.hours, 0);
                trendActuals.push(Number(actual.toFixed(2)));
            }
            trendColors.push(b === selectedBlockNum ? "#2e1065" : "rgba(93, 58, 155, 0.3)");
        }
    } else if (currentMode === "sprint") {
        trendTitleEl.textContent = "Consuntivo vs Preventivo per Sprint";
        trendDescEl.textContent = "Confronto sugli sprint rilevati rispetto al preventivo delle settimane coperte";
        planSeriesLabel = "Preventivo sprint (h)";

        const allSprints = [...new Set(
            validEntries.map((e) => resolveEntrySprint(e, weekPrimarySprint)).filter(Boolean)
        )].sort((a, b) => parseSprintNum(a) - parseSprintNum(b));

        allSprints.forEach((sp) => {
            const spEntries = validEntries.filter((e) => resolveEntrySprint(e, weekPrimarySprint) === sp);
            const spWeeks = [...new Set(spEntries.map((e) => e.week_number))].sort((a, b) => a - b);
            const wkRange = spWeeks.length === 1
                ? `S${spWeeks[0]}`
                : `S${spWeeks[0]}–S${spWeeks[spWeeks.length - 1]}`;

            trendLabels.push([sp, wkRange]);
            trendActuals.push(Number(spEntries.reduce((s, e) => s + e.hours, 0).toFixed(2)));
            trendPlans.push(
                spWeeks.reduce(
                    (acc, wn) => acc + roleKeys.reduce((rSum, rk) => rSum + plannedHoursForWeek(roles[rk], wn), 0),
                    0
                )
            );
            trendColors.push(sp === selectedSprint ? "#2e1065" : "rgba(93, 58, 155, 0.3)");
        });
    } else {
        trendTitleEl.textContent = "Consuntivo vs Preventivo settimanale";
        trendDescEl.textContent = `Andamento pianificato su tutte le ${projectWeeks} settimane rispetto alle ore rendicontate`;
        planSeriesLabel = "Preventivo settimanale (h)";

        const totalWeeks = Math.max(projectWeeks, lastLoggedWeek);
        const weekNums = Array.from({ length: totalWeeks }, (_, i) => i + 1);
        trendLabels = weekNums.map((wn) => {
            const sp = sprintLabelForWeek(validEntries, wn);
            return sp ? [`S${wn}`, sp] : `S${wn}`;
        });
        trendActuals = weekNums.map((wn) => {
            if (wn > lastLoggedWeek) return null;
            return Number(
                validEntries
                    .filter((e) => e.week_number === wn)
                    .reduce((s, e) => s + e.hours, 0)
                    .toFixed(2)
            );
        });
        trendPlans = weekNums.map((wn) =>
            roleKeys.reduce((acc, rk) => acc + plannedHoursForWeek(roles[rk], wn), 0)
        );
        trendColors = weekNums.map((wn) => {
            if (isFullProject) return "#5d3a9b";
            return wn === selectedWeekNum ? "#2e1065" : "rgba(93, 58, 155, 0.3)";
        });
    }

    if (weekChart) weekChart.destroy();
    weekChart = new Chart(document.getElementById("weekChart"), {
        type: "bar",
        data: {
            labels: trendLabels,
            datasets: [
                {
                    type: "line",
                    label: planSeriesLabel,
                    data: trendPlans,
                    borderColor: "#dc2626",
                    backgroundColor: "#dc2626",
                    borderDash: [6, 4],
                    borderWidth: 2,
                    tension: 0.15,
                    order: 1
                },
                {
                    type: "bar",
                    label: "Ore rendicontate (h)",
                    data: trendActuals,
                    backgroundColor: trendColors,
                    order: 2
                }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
    });

    // 6. Tabella Matrice Persona x Ruolo + Costo Effettivo Individuale
    document.getElementById("member-table-head").innerHTML = `
        <tr>
            <th>Membro</th>
            ${roleKeys.map((rk) => `<th class="num">${roles[rk].label}<small>€ ${roles[rk].hourly_rate}/h</small></th>`).join("")}
            <th class="num">Totale Ore</th>
            <th class="num">Costo Effettivo</th>
        </tr>
    `;

    document.getElementById("member-table-body").innerHTML = allMembers.map((member) => {
        let memberHours = 0;
        let memberCost = 0;

        const roleCells = roleKeys.map((rk) => {
            const h = filtered
                .filter((e) => e.member_name === member && e.role === rk)
                .reduce((s, e) => s + e.hours, 0);
            memberHours += h;
            memberCost += h * roles[rk].hourly_rate;
            return h > 0
                ? `<td class="num">${h.toFixed(1)} h</td>`
                : `<td class="num muted-zero">—</td>`;
        }).join("");

        return `
            <tr>
                <td><strong>${member}</strong></td>
                ${roleCells}
                <td class="num"><strong>${memberHours.toFixed(1)} h</strong></td>
                <td class="num"><strong>€ ${memberCost.toFixed(2)}</strong></td>
            </tr>
        `;
    }).join("");

    document.getElementById("member-table-foot").innerHTML = `
        <tr>
            <td>Totale Gruppo</td>
            ${roleKeys.map((rk) => `<td class="num">${actualByRole[rk].toFixed(1)} h</td>`).join("")}
            <td class="num">${totalActualHours.toFixed(1)} h</td>
            <td class="num">€ ${totalActualCost.toFixed(2)}</td>
        </tr>
    `;

    // 7. Tabella Riepilogo Budget per Ruolo
    document.getElementById("role-table-body").innerHTML = roleKeys.map((rk) => {
        const cfg = roles[rk];
        const planned = plannedByRole[rk];
        const actual = actualByRole[rk];
        const remaining = planned - actual;
        const cost = actual * cfg.hourly_rate;

        return `
            <tr>
                <td><strong>${cfg.label}</strong></td>
                <td class="num">€ ${cfg.hourly_rate}</td>
                <td class="num">${planned.toFixed(1)}</td>
                <td class="num">${actual.toFixed(1)}</td>
                <td class="num">${remaining.toFixed(1)}</td>
                <td class="num">€ ${cost.toFixed(2)}</td>
            </tr>
        `;
    }).join("");

    document.getElementById("role-table-foot").innerHTML = `
        <tr>
            <td>Totale</td>
            <td class="num">—</td>
            <td class="num">${totalPlannedHours.toFixed(1)}</td>
            <td class="num">${totalActualHours.toFixed(1)}</td>
            <td class="num">${remainingHours.toFixed(1)}</td>
            <td class="num">€ ${totalActualCost.toFixed(2)}</td>
        </tr>
    `;
};

const setMode = (mode) => {
    currentMode = mode;
    document.querySelectorAll(".mode-btn").forEach((btn) => {
        const active = btn.dataset.mode === mode;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-pressed", String(active));
    });
    populatePeriodSelect();
    render();
};

const init = async () => {
    const resp = await fetch("./data.json");
    rawData = await resp.json();

    const dt = new Date(rawData.generated_at).toLocaleString("it-IT");
    document.getElementById("meta-info").textContent = `${rawData.project_title} · Aggiornato il ${dt}`;
    if (rawData.is_mock) {
        document.getElementById("mock-banner").hidden = false;
    }

    document.querySelectorAll(".mode-btn").forEach((btn) => {
        btn.addEventListener("click", () => setMode(btn.dataset.mode));
    });
    document.getElementById("period-select").addEventListener("change", render);

    setMode("all");
};

document.addEventListener("DOMContentLoaded", () => {
    init().catch((err) => {
        document.getElementById("meta-info").textContent = `Errore caricamento data.json: ${err.message}`;
    });
});