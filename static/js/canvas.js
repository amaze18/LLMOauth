class PlotEditor {
    constructor(canvasId, onChange) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.onChange = onChange;
        
        // Define coordinate space (0 to 100 feet)
        this.coordMaxX = 100;
        this.coordMaxY = 100;
        
        this.vertices = [];
        this.footprint = null; // [[x,y], [x,y]]
        
        this.draggedVertex = null;
        this.hoveredVertex = null;
        this.vertexRadius = 6;
        
        this.setupEvents();
    }
    
    setVertices(coords) {
        this.vertices = coords.map(c => ({x: c[0], y: c[1]}));
        this.footprint = null;
        this.draw();
        this.triggerChange();
    }

    setFootprint(coords) {
        this.footprint = coords;
        this.draw();
    }
    
    addVertex() {
        if(this.vertices.length < 3) return;
        // Add halfway between last and first
        let last = this.vertices[this.vertices.length - 1];
        let first = this.vertices[0];
        this.vertices.push({
            x: Math.round((last.x + first.x) / 2),
            y: Math.round((last.y + first.y) / 2)
        });
        this.draw();
        this.triggerChange();
    }
    
    triggerChange() {
        if(this.onChange) {
            this.onChange(this.vertices.map(v => [v.x, v.y]));
        }
    }
    
    // Map world coords (feet) to canvas pixels
    toCanvas(worldX, worldY) {
        // Pad by 10%
        const padX = this.canvas.width * 0.1;
        const padY = this.canvas.height * 0.1;
        const usableW = this.canvas.width - 2*padX;
        const usableH = this.canvas.height - 2*padY;
        
        const px = padX + (worldX / this.coordMaxX) * usableW;
        const py = this.canvas.height - (padY + (worldY / this.coordMaxY) * usableH); // Invert Y
        return {x: px, y: py};
    }
    
    toWorld(canvasX, canvasY) {
        const padX = this.canvas.width * 0.1;
        const padY = this.canvas.height * 0.1;
        const usableW = this.canvas.width - 2*padX;
        const usableH = this.canvas.height - 2*padY;
        
        let wx = ((canvasX - padX) / usableW) * this.coordMaxX;
        let wy = ((this.canvas.height - canvasY - padY) / usableH) * this.coordMaxY;
        
        // Snap to integer feet
        return {x: Math.round(wx), y: Math.round(wy)};
    }
    
    draw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw grid
        this.ctx.strokeStyle = "rgba(255,255,255,0.05)";
        this.ctx.lineWidth = 1;
        for(let i=0; i<=100; i+=10) {
            let p1 = this.toCanvas(i, 0);
            let p2 = this.toCanvas(i, 100);
            this.ctx.beginPath(); this.ctx.moveTo(p1.x, p1.y); this.ctx.lineTo(p2.x, p2.y); this.ctx.stroke();
            
            let p3 = this.toCanvas(0, i);
            let p4 = this.toCanvas(100, i);
            this.ctx.beginPath(); this.ctx.moveTo(p3.x, p3.y); this.ctx.lineTo(p4.x, p4.y); this.ctx.stroke();
        }
        
        // Draw Compass Directions
        this.ctx.fillStyle = "rgba(255,255,255,0.3)";
        this.ctx.font = "bold 16px Inter";
        this.ctx.textAlign = "center";
        this.ctx.textBaseline = "middle";
        
        // North (Top Center)
        this.ctx.fillText("N (North)", this.canvas.width / 2, this.canvas.height * 0.05);
        // South (Bottom Center)
        this.ctx.fillText("S (South)", this.canvas.width / 2, this.canvas.height * 0.95);
        // West (Left Center)
        this.ctx.fillText("W", this.canvas.width * 0.04, this.canvas.height / 2);
        // East (Right Center)
        this.ctx.fillText("E", this.canvas.width * 0.96, this.canvas.height / 2);
        
        this.ctx.textAlign = "left"; // Reset for other text
        this.ctx.textBaseline = "alphabetic";
        
        // Footprint is no longer drawn on the canvas, only the plot boundary.
        if(this.footprint && this.footprint.length > 0) {
            // Footprint logic removed to emphasize 2-step AI pipeline
        }
        
        // Draw Polygon
        if(this.vertices.length >= 3) {
            this.ctx.fillStyle = "rgba(239, 68, 68, 0.05)";
            this.ctx.strokeStyle = "#ef4444";
            this.ctx.lineWidth = 3;
            this.ctx.beginPath();
            let start = this.toCanvas(this.vertices[0].x, this.vertices[0].y);
            this.ctx.moveTo(start.x, start.y);
            for(let i=1; i<this.vertices.length; i++) {
                let p = this.toCanvas(this.vertices[i].x, this.vertices[i].y);
                this.ctx.lineTo(p.x, p.y);
            }
            this.ctx.closePath();
            this.ctx.fill();
            this.ctx.stroke();
        }
        
        // Draw Vertices
        for(let i=0; i<this.vertices.length; i++) {
            let p = this.toCanvas(this.vertices[i].x, this.vertices[i].y);
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, this.vertexRadius, 0, Math.PI*2);
            this.ctx.fillStyle = (this.hoveredVertex === this.vertices[i] || this.draggedVertex === this.vertices[i]) ? "#fff" : "#ef4444";
            this.ctx.fill();
            this.ctx.strokeStyle = "#fff";
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
            
            // Text label
            this.ctx.fillStyle = "rgba(255,255,255,0.7)";
            this.ctx.font = "10px Inter";
            this.ctx.fillText(`(${this.vertices[i].x}, ${this.vertices[i].y})`, p.x + 10, p.y - 10);
        }
    }
    
    getMousePos(evt) {
        let rect = this.canvas.getBoundingClientRect();
        let scaleX = this.canvas.width / rect.width;
        let scaleY = this.canvas.height / rect.height;
        return {
            x: (evt.clientX - rect.left) * scaleX,
            y: (evt.clientY - rect.top) * scaleY
        };
    }
    
    getVertexAt(pos) {
        for(let i=0; i<this.vertices.length; i++) {
            let p = this.toCanvas(this.vertices[i].x, this.vertices[i].y);
            let dx = p.x - pos.x;
            let dy = p.y - pos.y;
            if(Math.sqrt(dx*dx + dy*dy) <= this.vertexRadius + 5) {
                return this.vertices[i];
            }
        }
        return null;
    }
    
    setupEvents() {
        this.canvas.addEventListener('mousedown', (e) => {
            let pos = this.getMousePos(e);
            let v = this.getVertexAt(pos);
            if(v) {
                this.draggedVertex = v;
                this.canvas.style.cursor = 'grabbing';
            }
        });
        
        this.canvas.addEventListener('mousemove', (e) => {
            let pos = this.getMousePos(e);
            
            if(this.draggedVertex) {
                let worldPos = this.toWorld(pos.x, pos.y);
                this.draggedVertex.x = Math.max(0, Math.min(this.coordMaxX, worldPos.x));
                this.draggedVertex.y = Math.max(0, Math.min(this.coordMaxY, worldPos.y));
                this.draw();
                return;
            }
            
            let v = this.getVertexAt(pos);
            if(v !== this.hoveredVertex) {
                this.hoveredVertex = v;
                this.canvas.style.cursor = v ? 'grab' : 'crosshair';
                this.draw();
            }
        });
        
        this.canvas.addEventListener('mouseup', (e) => {
            if(this.draggedVertex) {
                this.draggedVertex = null;
                this.canvas.style.cursor = 'grab';
                this.triggerChange(); // Validate after drag
            }
        });
        
        this.canvas.addEventListener('mouseleave', (e) => {
            if(this.draggedVertex) {
                this.draggedVertex = null;
                this.triggerChange();
            }
            this.hoveredVertex = null;
            this.draw();
        });
    }
}
