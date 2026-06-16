document.addEventListener("DOMContentLoaded", () => {
    // Presets
    const presets = {
        "l_shape": [[0, 8], [0, 84], [75, 84], [75, 88], [80, 88], [80, 8], [75, 8], [75, 0], [35, 0], [35, 8]],
        "rectangle": [[10, 10], [10, 90], [90, 90], [90, 10]],
        "t_shape": [[20, 10], [20, 70], [0, 70], [0, 90], [80, 90], [80, 70], [60, 70], [60, 10]],
        "blank": [[0, 0], [0, 50], [50, 50], [50, 0]]
    };

    let currentCoords = presets["l_shape"];
    let currentFootprint = [];
    
    // UI Elements
    const presetSelect = document.getElementById("preset-select");
    const addVertexBtn = document.getElementById("add-vertex-btn");
    const generateBtn = document.getElementById("generate-btn");
    const statusBox = document.getElementById("validation-status");
    const netAreaSpan = document.getElementById("net-area");
    const workflowSteps = document.getElementById("workflow-steps");
    const pipelineStatus = document.getElementById("pipeline-status");
    const pipelineStatusText = document.getElementById("pipeline-status-text");
    const finalResults = document.getElementById("final-results");
    const dxfBtn = document.getElementById("download-dxf-btn");
    
    // Setback and SBC inputs
    const setbackVerticalInput = document.getElementById("setback-vertical");
    const setbackHorizontalInput = document.getElementById("setback-horizontal");
    const customSbcInput = document.getElementById("custom-sbc");
    const customVastuInput = document.getElementById("custom-vastu");
    const customVastuStage3Input = document.getElementById("custom-vastu-stage3");

    // Initialize Canvas Editor
    const editor = new PlotEditor("plot-canvas", handleCoordsChange);
    editor.setVertices(currentCoords);
    

    
    // Events
    presetSelect.addEventListener("change", (e) => {
        currentCoords = presets[e.target.value];
        editor.setVertices(currentCoords);
    });
    
    addVertexBtn.addEventListener("click", () => {
        editor.addVertex();
    });
    
    generateBtn.addEventListener("click", runPipeline);
    
    // Re-validate when setbacks change
    setbackVerticalInput.addEventListener("change", () => handleCoordsChange(currentCoords));
    setbackHorizontalInput.addEventListener("change", () => handleCoordsChange(currentCoords));
    
    // Validate Initial
    handleCoordsChange(currentCoords);

    function handleCoordsChange(coords) {
        currentCoords = coords;
        
        const vertSetback = parseInt(setbackVerticalInput.value) || 5;
        const horizSetback = parseInt(setbackHorizontalInput.value) || 15;
        
        fetch('/api/validate_plot', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({coords: coords, setback_vertical: vertSetback, setback_horizontal: horizSetback})
        })
        .then(r => r.json())
        .then(data => {
            if(data.success) {
                statusBox.className = "status-box";
                statusBox.innerHTML = `<span class="icon">✅</span> Valid boundary. Footprint Net Area: <strong>${data.net_area}</strong> sq ft.`;
                editor.setFootprint(data.footprint_coords);
                currentFootprint = data.footprint_coords;
                generateBtn.disabled = false;
            } else {
                statusBox.className = "status-box error";
                statusBox.innerHTML = `<span class="icon">⚠️</span> ${data.error}`;
                editor.setFootprint([]);
                generateBtn.disabled = true;
            }
        })
        .catch(e => {
            statusBox.className = "status-box error";
            statusBox.innerHTML = `<span class="icon">⚠️</span> Network error validating plot.`;
            generateBtn.disabled = true;
        });
    }

    let eventSource = null;
    let currentSessionId = null;

    function runPipeline() {
        if(eventSource) {
            eventSource.close();
        }
        
        // Reset UI
        generateBtn.disabled = true;
        workflowSteps.innerHTML = '';
        finalResults.classList.add("hidden");
        pipelineStatus.classList.remove("hidden");
        pipelineStatusText.innerText = "Initializing Multi-Agent Pipeline...";
        
        const coordsStr = encodeURIComponent(JSON.stringify(currentCoords));
        const vertSetback = parseInt(setbackVerticalInput.value) || 5;
        const horizSetback = parseInt(setbackHorizontalInput.value) || 15;
        const customSbc = encodeURIComponent(customSbcInput.value);
        const customVastu = encodeURIComponent(customVastuInput.value);
        const customVastuStage3 = encodeURIComponent(customVastuStage3Input.value);
        eventSource = new EventSource(`/api/run_pipeline?coords=${coordsStr}&sv=${vertSetback}&sh=${horizSetback}&sbc=${customSbc}&vastu=${customVastu}&vastu_stage3=${customVastuStage3}`);
        
        eventSource.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            
            if(msg.type === "session_init") {
                currentSessionId = msg.session_id;
            }
            else if(msg.type === "step") {
                if(msg.data.footprint) {
                    currentFootprint = msg.data.footprint;
                    editor.setFootprint(currentFootprint);
                }
                renderStepCard(msg.data);
                updateStatusText(msg.data);
            } 
            else if(msg.type === "wait_for_feedback") {
                renderFeedbackUI(msg.iteration, msg.stage);
                pipelineStatusText.innerText = "Waiting for Human Feedback...";
            }
            else if(msg.type === "complete") {
                pipelineStatus.classList.add("hidden");
                generateBtn.disabled = false;
                eventSource.close();
                showFinalResults(msg.data);
            }
            else if(msg.type === "error") {
                pipelineStatus.classList.add("hidden");
                generateBtn.disabled = false;
                eventSource.close();
                alert("Pipeline Error:\n" + msg.message);
            }
        };
        
        eventSource.onerror = function() {
            pipelineStatus.classList.add("hidden");
            generateBtn.disabled = false;
            eventSource.close();
            alert("Connection to server lost.");
        };
    }
    
    function renderFeedbackUI(turn, stage = 1) {
        const cardId = `step-card-s${stage}-${turn}`;
        const card = document.getElementById(cardId);
        if(!card) return;
        
        const feedbackHtml = `
            <div id="feedback-ui-s${stage}-${turn}" style="margin-top: 15px; padding: 15px; background: rgba(99, 102, 241, 0.1); border: 1px solid #6366f1; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #818cf8; margin-bottom: 8px;">👨‍🎨 Human Architect Override</h4>
                <p style="font-size: 0.9rem; color: #d1d5db; margin-top: 0; margin-bottom: 10px;">Provide feedback to the AI for the next iteration, or skip to let it continue autonomously.</p>
                <textarea id="feedback-text-s${stage}-${turn}" rows="3" style="width: 100%; box-sizing: border-box; background: #1f2937; color: white; border: 1px solid #374151; border-radius: 4px; padding: 8px; margin-bottom: 10px;" placeholder="e.g. Expand the Kitchen by 3 feet..."></textarea>
                <div style="display: flex; gap: 10px;">
                    <button onclick="submitHumanFeedback(${turn}, false, ${stage})" style="background: #4f46e5; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">Submit Override</button>
                    <button onclick="submitHumanFeedback(${turn}, true, ${stage})" style="background: #374151; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">Skip / Continue</button>
                </div>
            </div>
        `;
        card.querySelector('.step-body').insertAdjacentHTML('beforeend', feedbackHtml);
    }

    window.submitHumanFeedback = function(turn, isSkip, stage = 1) {
        const uiDiv = document.getElementById(`feedback-ui-s${stage}-${turn}`);
        const textArea = document.getElementById(`feedback-text-s${stage}-${turn}`);
        const feedbackText = isSkip ? "" : textArea.value.trim();
        
        // Disable UI
        uiDiv.style.opacity = "0.5";
        uiDiv.style.pointerEvents = "none";
        pipelineStatusText.innerText = isSkip ? "Continuing autonomous loop..." : "Injecting human override...";
        
        fetch('/api/submit_feedback', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: currentSessionId,
                feedback: feedbackText
            })
        }).catch(e => console.error("Error submitting feedback:", e));
    };
    
    function updateStatusText(step) {
        if(step.verification_passed) {
            pipelineStatusText.innerText = "Success! Finalizing DXF...";
        } else if(!step.rooms || Object.keys(step.rooms).length === 0) {
            pipelineStatusText.innerText = `Iteration ${step.iteration}: Agent 1 Formulating constraints...`;
        } else {
            pipelineStatusText.innerText = `Iteration ${step.iteration}: Agent 2 analyzing failures...`;
        }
    }

    function renderStepCard(step) {
        const turn = step.iteration;
        const passed = step.verification_passed;
        const stage = step.stage || 1;
        const rooms = (stage === 3) ? (step.rooms_stage3 && Object.keys(step.rooms_stage3).length > 0) : (step.rooms && Object.keys(step.rooms).length > 0);
        
        let title = "";
        let colorClass = "";
        
        if(passed && turn > 0) {
            title = `Stage ${stage} | Iteration ${turn}: ✅ Success - Vastu Layout Found`;
            colorClass = "#22c55e";
        } else if(turn === 0) {
            title = `Step 1: 📐 Calculate House Footprint`;
            colorClass = "#6366f1";
        } else if(!rooms) {
            title = `Stage ${stage} | Iteration ${turn}: ❌ Solver Formulation Error`;
            colorClass = "#ef4444";
        } else {
            title = `Stage ${stage} | Iteration ${turn}: ⚠️ Vastu Verification Failed`;
            colorClass = "#eab308";
        }
        
        const cardId = `step-card-s${stage}-${turn}`;
        
        const cardHtml = `
            <div class="step-card" id="${cardId}">
                <div class="step-header" style="border-left: 4px solid ${colorClass}" onclick="document.getElementById('body-s${stage}-${turn}').classList.toggle('hidden')">
                    <span>${title}</span>
                    <span>▼</span>
                </div>
                <div class="step-body ${passed ? '' : 'hidden'}" id="body-s${stage}-${turn}">
                    <div class="verdict-box" style="background: ${colorClass}15; border: 1px solid ${colorClass}; color: ${colorClass}">
                        <b>Solver Verdict:</b> ${step.verification_report}
                    </div>
                    
                    <div class="tabs">
                        <button class="tab-btn active" onclick="switchTab('s${stage}-${turn}', 'layout')">🎨 Layout</button>
                        <button class="tab-btn" onclick="switchTab('s${stage}-${turn}', 'mentor')">💬 Mentor Feedback</button>
                        <button class="tab-btn" onclick="switchTab('s${stage}-${turn}', 'code')">💻 Z3 Code</button>
                    </div>
                    
                    <div id="tab-layout-s${stage}-${turn}" class="tab-content active">
                        ${(rooms || turn === 0) ? `<div id="plotly-step-s${stage}-${turn}" style="width:100%; height:380px;"></div>` : `<p style="color:#9ca3af">No room layout generated.</p>`}
                        ${step.dxf_filename ? `<div style="margin-top: 15px;"><a href="/download/${step.dxf_filename}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 600;">📥 Download AutoCAD DXF Blueprint</a></div>` : ''}
                    </div>
                    <div id="tab-mentor-s${stage}-${turn}" class="tab-content">
                        <p style="white-space: pre-wrap;">${step.mentor_feedback || 'No feedback generated.'}</p>
                    </div>
                    <div id="tab-code-s${stage}-${turn}" class="tab-content">
                        <pre>${step.agent1_code || 'No code generated.'}</pre>
                    </div>
                </div>
            </div>
        `;
        
        // Append or replace
        const existing = document.getElementById(cardId);
        if(existing) {
            existing.outerHTML = cardHtml;
        } else {
            workflowSteps.insertAdjacentHTML('beforeend', cardHtml);
        }
        
        if(rooms || turn === 0) {
            const layoutRooms = (stage === 3) ? step.rooms_stage3 : (step.rooms || {});
            plotLayoutPlotly(`plotly-step-s${stage}-${turn}`, currentCoords, currentFootprint, layoutRooms);
        }
    }
    
    function showFinalResults(data) {
        if(data.success) {
            finalResults.classList.remove("hidden");
            document.getElementById("metric-iterations").innerText = `${data.telemetry.iterations} / 5`;
            document.getElementById("metric-solved").innerText = `${data.telemetry.final_area} sqft`;
            document.getElementById("metric-time-stage1").innerText = `${data.telemetry.time_stage1 || 0}s`;
            document.getElementById("metric-time-stage2").innerText = `${data.telemetry.time_stage2 || 0}s`;
            
            plotLayoutPlotly("final-plotly-chart", currentCoords, currentFootprint, data.rooms, 600, data.rooms_stage3);
            
            if(data.dxf_filename) {
                dxfBtn.style.display = "inline-block";
                dxfBtn.href = `/download/${data.dxf_filename}`;
            }
        } else {
            alert("The Agent Pipeline failed to converge to a valid Vastu layout.");
        }
    }

    // Global tab switcher for inline html onclick
    window.switchTab = function(turn, tabName) {
        const card = document.getElementById(`body-${turn}`);
        card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        card.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        event.target.classList.add('active');
        document.getElementById(`tab-${tabName}-${turn}`).classList.add('active');
    };

    function plotLayoutPlotly(divId, boundary, footprint, rooms, height=380, rooms_stage3=null) {
        const traces = [];
        
        // Plot boundary
        const bx = boundary.map(p => p[0]);
        const by = boundary.map(p => p[1]);
        bx.push(bx[0]); by.push(by[0]); // close
        
        traces.push({
            x: bx, y: by,
            mode: 'lines',
            line: {color: '#ef4444', width: 2.5},
            name: 'Plot Boundary',
            fill: 'toself',
            fillcolor: 'rgba(239, 68, 68, 0.02)'
        });
        
        // Footprint
        if(footprint && footprint.length > 0) {
            const fx = footprint.map(p => p[0]);
            const fy = footprint.map(p => p[1]);
            traces.push({
                x: fx, y: fy,
                mode: 'lines',
                line: {color: '#6366f1', width: 1.5, dash: 'dash'},
                name: 'House Footprint'
            });
        }
        
        const roomColors = {
            "Living Room": "rgba(34, 197, 94, 0.6)",
            "Dining Area": "rgba(234, 179, 8, 0.6)",
            "Kitchen": "rgba(249, 115, 22, 0.6)",
            "Master Bedroom": "rgba(168, 85, 247, 0.6)",
            "Bedroom 2": "rgba(59, 130, 246, 0.6)",
            "Bedroom 3": "rgba(14, 165, 233, 0.6)",
            "Bathroom 1": "rgba(244, 63, 94, 0.6)",
            "Bathroom 2": "rgba(225, 29, 72, 0.6)",
            "Corridor": "rgba(107, 114, 128, 0.6)"
        };
        
        const annotations = [];
        
        const all_rooms = [];
        if (rooms) {
            for(const [name, coords] of Object.entries(rooms)) {
                all_rooms.push({name: name, coords: coords, isStage3: false});
            }
        }
        if (rooms_stage3) {
            for(const [name, coords] of Object.entries(rooms_stage3)) {
                all_rooms.push({name: name, coords: coords, isStage3: true});
            }
        }
        
        for(const item of all_rooms) {
            const name = item.name;
            const coords = item.coords;
            const isStage3 = item.isStage3;
            
            let rx = [], ry = [];
            let isRect = (coords.length === 4 && typeof coords[0] === 'number');
            let cx = 0, cy = 0;
            let areaLabel = "";
            let areaVal = 0;
            
            if (isRect) {
                const [x1, y1, x2, y2] = coords;
                rx = [x1, x2, x2, x1, x1];
                ry = [y1, y1, y2, y2, y1];
                cx = (x1 + x2) / 2;
                cy = (y1 + y2) / 2;
                const w = x2 - x1;
                const h = y2 - y1;
                areaLabel = `${w}x${h}`;
                areaVal = w * h;
            } else {
                rx = coords.map(p => p[0]);
                ry = coords.map(p => p[1]);
                rx.push(rx[0]); ry.push(ry[0]); // close
                
                // Approximate centroid using bounding box
                let minx = Math.min(...rx), maxx = Math.max(...rx);
                let miny = Math.min(...ry), maxy = Math.max(...ry);
                cx = (minx + maxx) / 2;
                cy = (miny + maxy) / 2;
                
                // Approximate area for tooltip
                // shoelace formula
                for(let i=0; i<coords.length; i++) {
                    let p1 = coords[i], p2 = coords[(i+1)%coords.length];
                    areaVal += (p1[0]*p2[1] - p2[0]*p1[1]);
                }
                areaVal = Math.round(Math.abs(areaVal / 2));
                areaLabel = `${areaVal} sqft`;
            }

            let fillcolor = roomColors[name] || "rgba(255, 255, 255, 0.5)";
            let linecolor = 'rgba(255, 255, 255, 0.3)';
            let dashStyle = 'solid';
            
            if (isStage3) {
                // Different styling for stage 3: dashed borders, slightly offset label, transparent cyan fill
                fillcolor = "rgba(0, 255, 255, 0.15)";
                linecolor = "rgba(0, 255, 255, 0.8)";
                dashStyle = 'dot';
            }
            
            traces.push({
                x: rx,
                y: ry,
                mode: 'lines',
                line: {color: linecolor, width: isStage3 ? 2.5 : 1.5, dash: dashStyle},
                fill: 'toself',
                fillcolor: fillcolor,
                name: (isStage3 ? "1st Floor: " : "GF: ") + name,
                hoverinfo: 'text',
                hovertext: `<b>${isStage3 ? "1st Floor: " : ""}${name}</b><br>Area: ${areaVal}`
            });
            
            annotations.push({
                x: cx,
                y: cy + (isStage3 ? 3 : 0), // Offset slightly so text doesn't perfectly overlap
                text: `<b>${isStage3 ? "[1F] " : ""}${name}</b><br>${areaLabel}`,
                showarrow: false,
                font: {size: 11, color: isStage3 ? '#0ff' : 'white'}
            });
        }
        
        const layout = {
            plot_bgcolor: "#030712",
            paper_bgcolor: "rgba(0,0,0,0)",
            xaxis: {
                gridcolor: "rgba(255, 255, 255, 0.05)",
                zeroline: false,
                scaleanchor: "y",
                scaleratio: 1
            },
            yaxis: {
                gridcolor: "rgba(255, 255, 255, 0.05)",
                zeroline: false
            },
            showlegend: false,
            height: height,
            margin: {l: 20, r: 20, t: 20, b: 20},
            annotations: annotations
        };
        
        Plotly.newPlot(divId, traces, layout, {displayModeBar: false});
    }
});
