// Wireframe Terrain - Synthwave/Tron style (High Quality)
import * as THREE from 'three';

const canvas = document.getElementById('bg');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// Mouse tracking
const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
document.addEventListener('mousemove', (e) => {
    mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
});

// Colors
const colors = {
    grid: '#64ffda',
    gridDim: '#1a3a4a',
    sun1: '#ff2a6d',
    sun2: '#d946ef',
    sun3: '#05d9e8',
};

// ============================================
// WORLD SETUP
// ============================================
// Camera: positioned above ground, looking at horizon
// Ground plane (terrain): y = 0, extends toward -z (horizon)
// Sky: everything above y = 0
// Sun: at horizon height (y ~ 0), far away (-z)
// Stars: in sky only (y > 0)
// ============================================

// Terrain shader - waves coming FROM the horizon with perspective
const terrainVertexShader = `
    uniform float uTime;
    uniform float uMouseX;

    varying vec2 vUv;
    varying float vElevation;
    varying float vDistanceFromCenter;
    varying float vDepth;

    // Simplex noise functions
    vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

    float snoise(vec2 v) {
        const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                           -0.577350269189626, 0.024390243902439);
        vec2 i  = floor(v + dot(v, C.yy));
        vec2 x0 = v -   i + dot(i, C.xx);
        vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
        vec4 x12 = x0.xyxy + C.xxzz;
        x12.xy -= i1;
        i = mod289(i);
        vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
        vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
        m = m*m;
        m = m*m;
        vec3 x = 2.0 * fract(p * C.www) - 1.0;
        vec3 h = abs(x) - 0.5;
        vec3 ox = floor(x + 0.5);
        vec3 a0 = x - ox;
        m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
        vec3 g;
        g.x  = a0.x  * x0.x  + h.x  * x0.y;
        g.yz = a0.yz * x12.xz + h.yz * x12.yw;
        return 130.0 * dot(m, g);
    }

    void main() {
        vUv = uv;

        vec3 pos = position;

        // vUv.y: 0 = near edge, 1 = far edge (PlaneGeometry default)
        // We want: 0 = horizon (far), 1 = camera (near)
        float nearness = 1.0 - vUv.y;
        vDepth = vUv.y;

        // Moving terrain - waves coming FROM horizon toward camera
        // pos.y is the local Y which becomes world -Z after rotation
        float movingY = pos.y - uTime * 2.0;

        // Multi-octave noise for terrain
        float elevation = 0.0;
        elevation += snoise(vec2(pos.x * 0.08, movingY * 0.08)) * 3.0;
        elevation += snoise(vec2(pos.x * 0.15, movingY * 0.15)) * 1.5;
        elevation += snoise(vec2(pos.x * 0.3, movingY * 0.3)) * 0.7;
        elevation += snoise(vec2(pos.x * 0.6, movingY * 0.6)) * 0.3;

        // PERSPECTIVE: waves get smaller toward horizon, bigger near camera
        // nearness: 0 = far (horizon), 1 = near (camera)
        float perspectiveScale = 0.2 + 0.8 * pow(nearness, 0.7);
        elevation *= perspectiveScale;

        // Mouse influence (stronger near camera)
        float mouseWave = sin(pos.x * 1.5 + uMouseX * 4.0) * 0.5;
        elevation += mouseWave * nearness;

        // Smooth X edges
        float edgeFadeX = smoothstep(0.0, 0.15, vUv.x) * smoothstep(1.0, 0.85, vUv.x);
        elevation *= edgeFadeX;

        // Distance from center for coloring
        vDistanceFromCenter = abs(pos.x) / 20.0;

        // After -90deg X rotation: local Z becomes world Y (up)
        pos.z = elevation;
        vElevation = elevation;

        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
`;

const terrainFragmentShader = `
    uniform float uTime;
    uniform vec3 uColorGrid;
    uniform vec3 uColorDim;

    varying vec2 vUv;
    varying float vElevation;
    varying float vDistanceFromCenter;
    varying float vDepth;

    void main() {
        // Base color based on elevation
        float elevationNorm = clamp((vElevation + 2.0) / 7.0, 0.0, 1.0);
        vec3 color = mix(uColorDim, uColorGrid, elevationNorm * 0.6);

        // Pulsing glow on higher elevations
        float pulse = sin(uTime * 2.0 + vElevation * 2.0) * 0.5 + 0.5;
        color += uColorGrid * pulse * elevationNorm * 0.25;

        // Grid lines
        float gridX = 1.0 - smoothstep(0.0, 0.04, abs(fract(vUv.x * 60.0) - 0.5) * 2.0);
        float gridY = 1.0 - smoothstep(0.0, 0.04, abs(fract(vUv.y * 100.0) - 0.5) * 2.0);
        float grid = max(gridX, gridY);

        color += uColorGrid * grid * (0.1 + elevationNorm * 0.3);

        // Distance fog - fade toward horizon (vDepth: 0=near, 1=far)
        float nearness = 1.0 - vDepth;
        float fog = 0.3 + 0.7 * nearness;
        color *= fog;

        // Edge glow
        float edgeGlow = (1.0 - vDistanceFromCenter) * 0.1;
        color += uColorGrid * edgeGlow * fog;

        gl_FragColor = vec4(color, 1.0);
    }
`;

// Create terrain - ground plane at y=0, extends from camera toward horizon
const terrainGeometry = new THREE.PlaneGeometry(60, 80, 200, 350);
const terrainMaterial = new THREE.ShaderMaterial({
    uniforms: {
        uTime: { value: 0 },
        uMouseX: { value: 0 },
        uColorGrid: { value: new THREE.Color(colors.grid) },
        uColorDim: { value: new THREE.Color(colors.gridDim) },
    },
    vertexShader: terrainVertexShader,
    fragmentShader: terrainFragmentShader,
    wireframe: true,
    transparent: true,
});

const terrain = new THREE.Mesh(terrainGeometry, terrainMaterial);
// Rotate to be horizontal (ground plane), facing up
terrain.rotation.x = -Math.PI * 0.5;
terrain.position.y = -2;
terrain.position.z = -35;  // Center at -35, extends from z=5 to z=-75
scene.add(terrain);

// Sun - positioned AT the horizon (y slightly above 0, far in -z)
const sunGeometry = new THREE.CircleGeometry(4, 128);
const sunMaterial = new THREE.ShaderMaterial({
    uniforms: {
        uColor1: { value: new THREE.Color(colors.sun1) },
        uColor2: { value: new THREE.Color(colors.sun2) },
        uColor3: { value: new THREE.Color(colors.sun3) },
        uTime: { value: 0 },
    },
    vertexShader: `
        varying vec2 vUv;
        void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `,
    fragmentShader: `
        uniform vec3 uColor1;
        uniform vec3 uColor2;
        uniform vec3 uColor3;
        uniform float uTime;
        varying vec2 vUv;

        void main() {
            // Vertical gradient (bottom to top)
            vec3 color = mix(uColor1, uColor2, vUv.y);
            color = mix(color, uColor3, smoothstep(0.7, 1.0, vUv.y));

            // Horizontal scanlines (bottom half only)
            float scanline = step(0.5, fract(vUv.y * 30.0));
            float scanMask = step(vUv.y, 0.5);
            color = mix(color, color * 0.1, scanline * scanMask);

            // Crisp circle edge
            float dist = length(vUv - 0.5) * 2.0;
            float alpha = 1.0 - smoothstep(0.95, 1.0, dist);

            gl_FragColor = vec4(color, alpha);
        }
    `,
    transparent: true,
});

const sun = new THREE.Mesh(sunGeometry, sunMaterial);
// Sun at horizon: terrain is at y=-2, sun bottom should be there
// Sun radius is 4, so center at y=2 puts bottom at y=-2 (horizon)
sun.position.set(0, 2, -60);
scene.add(sun);

// Sun glow
const sunGlowGeometry = new THREE.CircleGeometry(7, 128);
const sunGlowMaterial = new THREE.ShaderMaterial({
    uniforms: {
        uColor: { value: new THREE.Color(colors.sun1) },
    },
    vertexShader: `
        varying vec2 vUv;
        void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `,
    fragmentShader: `
        uniform vec3 uColor;
        varying vec2 vUv;
        void main() {
            float dist = length(vUv - 0.5) * 2.0;
            float alpha = smoothstep(1.0, 0.15, dist) * 0.4;
            gl_FragColor = vec4(uColor, alpha);
        }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
});

const sunGlow = new THREE.Mesh(sunGlowGeometry, sunGlowMaterial);
sunGlow.position.set(0, 2, -60.1);
scene.add(sunGlow);

// Stars - SKY ONLY (above terrain horizon)
const starsGeometry = new THREE.BufferGeometry();
const starsCount = 300;
const starsPositions = new Float32Array(starsCount * 3);
const starsSizes = new Float32Array(starsCount);
const starsSpeed = new Float32Array(starsCount);

for (let i = 0; i < starsCount; i++) {
    starsPositions[i * 3] = (Math.random() - 0.5) * 100;       // X: wide spread
    starsPositions[i * 3 + 1] = Math.random() * 20 + 5;        // Y: 5 to 25 (sky, above horizon)
    starsPositions[i * 3 + 2] = -Math.random() * 60 - 15;      // Z: -15 to -75
    starsSizes[i] = Math.random() * 2.0 + 0.5;
    starsSpeed[i] = Math.random() * 0.3 + 0.15;
}

starsGeometry.setAttribute('position', new THREE.BufferAttribute(starsPositions, 3));
starsGeometry.setAttribute('size', new THREE.BufferAttribute(starsSizes, 1));
starsGeometry.setAttribute('speed', new THREE.BufferAttribute(starsSpeed, 1));

const starsMaterial = new THREE.ShaderMaterial({
    uniforms: {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color('#ffffff') },
    },
    vertexShader: `
        attribute float size;
        attribute float speed;
        uniform float uTime;
        varying float vAlpha;

        void main() {
            // Stars move toward camera (simulate forward motion through space)
            vec3 pos = position;
            float zRange = 50.0;
            float zOffset = mod(uTime * speed * 5.0, zRange);
            pos.z = position.z + zOffset;

            // Wrap around when past camera
            if (pos.z > 0.0) {
                pos.z -= zRange;
            }

            vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
            gl_PointSize = size * (300.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;

            // Twinkle
            vAlpha = 0.5 + 0.5 * sin(uTime * 2.5 + position.x * 3.0 + position.y * 2.0);
        }
    `,
    fragmentShader: `
        uniform vec3 uColor;
        varying float vAlpha;

        void main() {
            float dist = length(gl_PointCoord - 0.5) * 2.0;
            float alpha = 1.0 - smoothstep(0.0, 1.0, dist);
            gl_FragColor = vec4(uColor, alpha * vAlpha * 0.6);
        }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
});

const stars = new THREE.Points(starsGeometry, starsMaterial);
scene.add(stars);

// Camera - above ground, looking toward horizon
camera.position.set(0, 6, 12);
camera.lookAt(0, 0, -40);

// Animation
function animate() {
    requestAnimationFrame(animate);

    const time = performance.now() * 0.001;

    // Smooth mouse interpolation
    mouse.x += (mouse.targetX - mouse.x) * 0.05;
    mouse.y += (mouse.targetY - mouse.y) * 0.05;

    // Update uniforms
    terrainMaterial.uniforms.uTime.value = time;
    terrainMaterial.uniforms.uMouseX.value = mouse.x;
    sunMaterial.uniforms.uTime.value = time;
    starsMaterial.uniforms.uTime.value = time;

    // Subtle camera movement
    camera.position.x = mouse.x * 2;
    camera.position.y = 6 + mouse.y * 1;
    camera.lookAt(mouse.x * 0.5, 0, -40);

    renderer.render(scene, camera);
}

// Handle resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
