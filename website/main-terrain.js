// Wireframe Terrain - Tron/Synthwave style
import * as THREE from 'three';

const canvas = document.getElementById('bg');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// Mouse
const mouse = { x: 0, y: 0 };
document.addEventListener('mousemove', (e) => {
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
});

// Terrain
const terrainWidth = 100;
const terrainHeight = 100;
const terrainGeometry = new THREE.PlaneGeometry(20, 20, terrainWidth, terrainHeight);

const terrainMaterial = new THREE.ShaderMaterial({
    uniforms: {
        uTime: { value: 0 },
        uColor1: { value: new THREE.Color('#0a0a1a') },
        uColor2: { value: new THREE.Color('#64ffda') },
    },
    vertexShader: `
        uniform float uTime;
        varying vec2 vUv;
        varying float vElevation;

        // Simplex noise
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

            // Moving terrain
            float movingY = pos.y + uTime * 0.5;

            // Multiple noise layers
            float elevation = snoise(vec2(pos.x * 0.3, movingY * 0.3)) * 1.0;
            elevation += snoise(vec2(pos.x * 0.6, movingY * 0.6)) * 0.5;
            elevation += snoise(vec2(pos.x * 1.2, movingY * 1.2)) * 0.25;

            // Fade out at edges
            float edgeFade = smoothstep(0.0, 0.3, vUv.x) * smoothstep(1.0, 0.7, vUv.x);
            elevation *= edgeFade;

            pos.z = elevation;
            vElevation = elevation;

            gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
        }
    `,
    fragmentShader: `
        uniform vec3 uColor1;
        uniform vec3 uColor2;
        varying vec2 vUv;
        varying float vElevation;

        void main() {
            // Color based on elevation
            float mixStrength = (vElevation + 1.0) * 0.5;
            vec3 color = mix(uColor1, uColor2, mixStrength);

            // Grid lines glow
            float gridX = smoothstep(0.98, 1.0, fract(vUv.x * 50.0));
            float gridY = smoothstep(0.98, 1.0, fract(vUv.y * 50.0));
            float grid = max(gridX, gridY);
            color += uColor2 * grid * 0.3;

            // Fade at distance
            float fade = smoothstep(1.0, 0.3, vUv.y);
            color *= fade;

            gl_FragColor = vec4(color, 1.0);
        }
    `,
    wireframe: true,
    transparent: true,
});

const terrain = new THREE.Mesh(terrainGeometry, terrainMaterial);
terrain.rotation.x = -Math.PI * 0.5 + 0.3;
terrain.position.y = -2;
terrain.position.z = -3;
scene.add(terrain);

// Add horizon glow
const glowGeometry = new THREE.PlaneGeometry(30, 5);
const glowMaterial = new THREE.ShaderMaterial({
    uniforms: {
        uColor: { value: new THREE.Color('#64ffda') },
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
            float alpha = smoothstep(0.0, 0.5, vUv.y) * smoothstep(1.0, 0.5, vUv.y);
            alpha *= 0.3;
            gl_FragColor = vec4(uColor, alpha);
        }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
});

const glow = new THREE.Mesh(glowGeometry, glowMaterial);
glow.position.y = 0.5;
glow.position.z = -8;
scene.add(glow);

// Sun
const sunGeometry = new THREE.CircleGeometry(1.5, 64);
const sunMaterial = new THREE.ShaderMaterial({
    uniforms: {
        uColor1: { value: new THREE.Color('#ff6b6b') },
        uColor2: { value: new THREE.Color('#ffd93d') },
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
        varying vec2 vUv;
        void main() {
            vec3 color = mix(uColor1, uColor2, vUv.y);

            // Horizontal lines
            float lines = step(0.5, fract(vUv.y * 15.0));
            color = mix(color, color * 0.3, lines * step(0.5, vUv.y));

            gl_FragColor = vec4(color, 1.0);
        }
    `,
});

const sun = new THREE.Mesh(sunGeometry, sunMaterial);
sun.position.y = 2;
sun.position.z = -10;
scene.add(sun);

camera.position.z = 5;
camera.position.y = 1;

function animate() {
    requestAnimationFrame(animate);

    const time = performance.now() * 0.001;
    terrainMaterial.uniforms.uTime.value = time;

    // Subtle camera movement with mouse
    camera.position.x = mouse.x * 0.5;
    camera.rotation.y = mouse.x * 0.05;

    renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
