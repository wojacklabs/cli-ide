import * as THREE from 'three';
import { FontLoader } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';

// Scene setup
const canvas = document.getElementById('bg');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// Mouse tracking
const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

document.addEventListener('mousemove', (e) => {
    mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
});

// Liquid text shader
const vertexShader = `
    uniform float uTime;
    uniform float uMouseX;
    uniform float uMouseY;

    varying vec2 vUv;
    varying vec3 vPosition;

    // Simplex noise
    vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
    vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

    float snoise(vec3 v) {
        const vec2 C = vec2(1.0/6.0, 1.0/3.0);
        const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

        vec3 i  = floor(v + dot(v, C.yyy));
        vec3 x0 = v - i + dot(i, C.xxx);

        vec3 g = step(x0.yzx, x0.xyz);
        vec3 l = 1.0 - g;
        vec3 i1 = min(g.xyz, l.zxy);
        vec3 i2 = max(g.xyz, l.zxy);

        vec3 x1 = x0 - i1 + C.xxx;
        vec3 x2 = x0 - i2 + C.yyy;
        vec3 x3 = x0 - D.yyy;

        i = mod289(i);
        vec4 p = permute(permute(permute(
            i.z + vec4(0.0, i1.z, i2.z, 1.0))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0))
            + i.x + vec4(0.0, i1.x, i2.x, 1.0));

        float n_ = 1.0/7.0;
        vec3 ns = n_ * D.wyz - D.xzx;
        vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
        vec4 x_ = floor(j * ns.z);
        vec4 y_ = floor(j - 7.0 * x_);
        vec4 x = x_ * ns.x + ns.yyyy;
        vec4 y = y_ * ns.x + ns.yyyy;
        vec4 h = 1.0 - abs(x) - abs(y);
        vec4 b0 = vec4(x.xy, y.xy);
        vec4 b1 = vec4(x.zw, y.zw);
        vec4 s0 = floor(b0)*2.0 + 1.0;
        vec4 s1 = floor(b1)*2.0 + 1.0;
        vec4 sh = -step(h, vec4(0.0));
        vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
        vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
        vec3 p0 = vec3(a0.xy, h.x);
        vec3 p1 = vec3(a0.zw, h.y);
        vec3 p2 = vec3(a1.xy, h.z);
        vec3 p3 = vec3(a1.zw, h.w);
        vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
        p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
        vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
        m = m * m;
        return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
    }

    void main() {
        vUv = uv;
        vPosition = position;

        vec3 pos = position;

        // Liquid distortion based on position and time
        float distortionX = snoise(vec3(pos.x * 0.5 + uTime * 0.3, pos.y * 0.5, pos.z * 0.5)) * 0.15;
        float distortionY = snoise(vec3(pos.x * 0.5, pos.y * 0.5 + uTime * 0.25, pos.z * 0.5 + uTime * 0.1)) * 0.15;
        float distortionZ = snoise(vec3(pos.x * 0.3 + uTime * 0.2, pos.y * 0.3, pos.z * 0.3)) * 0.1;

        // Mouse influence - stronger near mouse position
        float mouseDistX = pos.x * 0.3 - uMouseX * 2.0;
        float mouseDistY = pos.y * 0.3 - uMouseY * 2.0;
        float mouseDist = sqrt(mouseDistX * mouseDistX + mouseDistY * mouseDistY);
        float mouseInfluence = smoothstep(3.0, 0.0, mouseDist);

        // Apply extra distortion near mouse
        distortionX += snoise(vec3(pos.x * 2.0 + uTime, pos.y * 2.0, uMouseX * 3.0)) * mouseInfluence * 0.3;
        distortionY += snoise(vec3(pos.x * 2.0, pos.y * 2.0 + uTime, uMouseY * 3.0)) * mouseInfluence * 0.3;

        pos.x += distortionX;
        pos.y += distortionY;
        pos.z += distortionZ;

        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
`;

const fragmentShader = `
    uniform float uTime;
    uniform vec3 uColor1;
    uniform vec3 uColor2;

    varying vec2 vUv;
    varying vec3 vPosition;

    void main() {
        // Gradient based on original position
        float gradient = smoothstep(-2.0, 2.0, vPosition.x);

        // Add subtle time-based color shift
        float shift = sin(uTime * 0.5 + vPosition.x * 0.5) * 0.1;

        vec3 color = mix(uColor1, uColor2, gradient + shift);

        // Add subtle glow at edges
        float edge = 1.0 - smoothstep(0.0, 0.1, abs(vPosition.z));
        color += vec3(0.1, 0.2, 0.3) * edge * 0.5;

        gl_FragColor = vec4(color, 1.0);
    }
`;

// Material
const material = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
        uTime: { value: 0 },
        uMouseX: { value: 0 },
        uMouseY: { value: 0 },
        uColor1: { value: new THREE.Color('#64ffda') },
        uColor2: { value: new THREE.Color('#4a9eff') },
    },
    side: THREE.DoubleSide,
});

// Load font and create text
const fontLoader = new FontLoader();
let textMesh = null;

fontLoader.load(
    'https://threejs.org/examples/fonts/helvetiker_bold.typeface.json',
    (font) => {
        const textGeometry = new TextGeometry('CLI-IDE', {
            font: font,
            size: 1,
            height: 0.3,
            curveSegments: 32,
            bevelEnabled: true,
            bevelThickness: 0.03,
            bevelSize: 0.02,
            bevelOffset: 0,
            bevelSegments: 8,
        });

        // Center the geometry
        textGeometry.computeBoundingBox();
        const centerOffset = new THREE.Vector3();
        textGeometry.boundingBox.getCenter(centerOffset);
        textGeometry.translate(-centerOffset.x, -centerOffset.y, -centerOffset.z);

        textMesh = new THREE.Mesh(textGeometry, material);
        scene.add(textMesh);

        // Add wireframe overlay
        const wireMaterial = new THREE.MeshBasicMaterial({
            color: '#64ffda',
            wireframe: true,
            transparent: true,
            opacity: 0.05,
        });
        const wireframe = new THREE.Mesh(textGeometry.clone(), wireMaterial);
        textMesh.add(wireframe);
    }
);

// Add floating particles
const particlesGeometry = new THREE.BufferGeometry();
const particlesCount = 300;
const posArray = new Float32Array(particlesCount * 3);

for (let i = 0; i < particlesCount * 3; i++) {
    posArray[i] = (Math.random() - 0.5) * 12;
}

particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

const particlesMaterial = new THREE.PointsMaterial({
    size: 0.015,
    color: '#64ffda',
    transparent: true,
    opacity: 0.3,
    blending: THREE.AdditiveBlending,
});

const particles = new THREE.Points(particlesGeometry, particlesMaterial);
scene.add(particles);

camera.position.z = 5;

// Animation
function animate() {
    requestAnimationFrame(animate);

    const time = performance.now() * 0.001;

    // Smooth mouse interpolation
    mouse.x += (mouse.targetX - mouse.x) * 0.05;
    mouse.y += (mouse.targetY - mouse.y) * 0.05;

    // Update uniforms
    material.uniforms.uTime.value = time;
    material.uniforms.uMouseX.value = mouse.x;
    material.uniforms.uMouseY.value = mouse.y;

    // Subtle rotation based on mouse
    if (textMesh) {
        textMesh.rotation.x = mouse.y * 0.1;
        textMesh.rotation.y = mouse.x * 0.1;
    }

    // Animate particles
    particles.rotation.y = time * 0.02;

    renderer.render(scene, camera);
}

// Handle resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
