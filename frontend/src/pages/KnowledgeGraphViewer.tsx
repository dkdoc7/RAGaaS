import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface GraphNode {
    id: string;
    label: string;
    group: string;
    color?: string;
    val?: number;
}

interface GraphLink {
    source: string;
    target: string;
    label: string;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

const GraphViewer: React.FC = () => {
    const params = new URLSearchParams(window.location.search);
    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const fgRef = useRef<any>(null);

    const entity = params.get('entity');
    const kbId = params.get('kb_id');
    const backend = params.get('backend') || 'neo4j';

    const [showLabels, setShowLabels] = useState(false);

    useEffect(() => {
        if (!entity || !kbId) {
            setError("Missing required parameters: entity, kb_id");
            setLoading(false);
            return;
        }

        const fetchData = async () => {
            setLoading(true);
            try {
                const response = await fetch(`http://localhost:8000/api/retrieval/graph/expand?kb_id=${kbId}&entity=${encodeURIComponent(entity)}&backend=${backend}`);
                if (!response.ok) {
                    throw new Error(`API Error: ${response.statusText}`);
                }
                const data = await response.json();

                const processedNodes = data.nodes.map((n: any) => ({
                    ...n,
                    val: n.id === entity ? 20 : 10,  // Bigger size for center node
                    color: n.id === entity ? '#ff4444' : (n.group === 'Chunk' ? '#4488ff' : '#44ff88')
                }));

                setGraphData({
                    nodes: processedNodes,
                    links: data.links
                });

            } catch (err: any) {
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [entity, kbId, backend]);

    useEffect(() => {
        if (fgRef.current) {
            // Apply custom forces dynamically
            const fg = fgRef.current;

            // Stronger repulsion to prevent clustering
            fg.d3Force('charge').strength(-400).distanceMax(600);

            // Adjust link distance
            fg.d3Force('link').distance(100);

            // If possible, add collision (requires d3-force, skipping for now as we don't have d3 imported)
            // But strong charge usually handles it well enough for small graphs.

            // Re-heat simulation
            fg.d3ReheatSimulation();
        }
    }, [graphData]);

    const handleNodeClick = useCallback((node: any) => {
        fgRef.current?.centerAt(node.x, node.y, 1000);
        fgRef.current?.zoom(3, 2000);
    }, []);

    if (loading) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#111', color: '#fff' }}>Loading Graph...</div>;
    if (error) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#111', color: '#ff4444' }}>Error: {error}</div>;

    return (
        <div style={{ width: '100vw', height: '100vh', background: '#000011' }}>
            <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 100, color: '#fff', background: 'rgba(0,0,0,0.7)', padding: '10px', borderRadius: '5px' }}>
                <h2 style={{ margin: 0 }}>{entity}</h2>
                <small>Source: {backend}</small>
            </div>

            <div style={{ position: 'absolute', top: 20, right: 20, zIndex: 100, color: '#fff', background: 'rgba(0,0,0,0.7)', padding: '10px', borderRadius: '5px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                    type="checkbox"
                    id="showLabels"
                    checked={showLabels}
                    onChange={(e) => setShowLabels(e.target.checked)}
                    style={{ cursor: 'pointer' }}
                />
                <label htmlFor="showLabels" style={{ cursor: 'pointer', fontSize: '0.9rem' }}>Show Labels</label>
            </div>

            <ForceGraph2D
                ref={fgRef}
                graphData={graphData}
                nodeLabel="label"
                nodeColor="color"
                nodeRelSize={8}

                nodeCanvasObject={(node: any, ctx, globalScale) => {
                    const label = node.label;
                    const fontSize = 12 / globalScale;
                    const r = node.val ? Math.sqrt(node.val) * 2 : 4;  // rough approximation of nodeRelSize logic

                    // Draw Node
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
                    ctx.fillStyle = node.color || '#fff';
                    ctx.fill();

                    // Selection glow could go here

                    // Draw Label if enabled
                    if (showLabels) {
                        ctx.font = `${fontSize}px Sans-Serif`;
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillStyle = 'white';
                        // Draw below the node
                        ctx.fillText(label, node.x, node.y + r + fontSize);
                    }
                }}
                nodeCanvasObjectMode={() => 'replace'} // We draw everything ourselves

                linkLabel={link => (link as any).label}
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1}
                linkWidth={2}
                linkColor={() => 'rgba(255,255,255,0.4)'}
                onNodeClick={handleNodeClick}
                backgroundColor="#000011"
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.3}
                cooldownTicks={100}
                onEngineStop={() => fgRef.current?.zoomToFit(400)}
            />
        </div>
    );
};

export default GraphViewer;
