import * as THREE from 'three';

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

// Liquid blob shader
const vertexShader = `
    uniform float uTime;
    uniform float uMouseX;
    uniform float uMouseY;
    uniform float uDistortion;

    varying vec2 vUv;
    varying float vDisplacement;

    // Simplex 3D noise
    vec4 permute(vec4 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
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

        i = mod(i, 289.0);
        vec4 p = permute(permute(permute(
            i.z + vec4(0.0, i1.z, i2.z, 1.0))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0))
            + i.x + vec4(0.0, i1.x, i2.x, 1.0));

        float n_ = 1.0/7.0;
        vec3 ns = n_ * D.wyz - D.xzx;

        vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

        vec4 x_ = floor(j * ns.z);
        vec4 y_ = floor(j - 7.0 * x_);

        vec4 x = x_ *ns.x + ns.yyyy;
        vec4 y = y_ *ns.x + ns.yyyy;
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
        p0 *= norm.x;
        p1 *= norm.y;
        p2 *= norm.z;
        p3 *= norm.w;

        vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
        m = m * m;
        return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
    }

    void main() {
        vUv = uv;

        vec3 pos = position;

        // Multi-layer noise for organic movement
        float noise1 = snoise(vec3(pos.x * 1.5 + uTime * 0.3, pos.y * 1.5, pos.z * 1.5));
        float noise2 = snoise(vec3(pos.x * 3.0 - uTime * 0.2, pos.y * 3.0 + uTime * 0.1, pos.z * 3.0)) * 0.5;
        float noise3 = snoise(vec3(pos.x * 0.5 + uTime * 0.1, pos.y * 0.5 - uTime * 0.15, pos.z * 0.5)) * 2.0;

        // Mouse influence
        float mouseInfluence = (uMouseX * pos.x + uMouseY * pos.y) * 0.3;

        float displacement = (noise1 + noise2 + noise3) * uDistortion + mouseInfluence;
        vDisplacement = displacement;

        pos += normal * displacement;

        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
`;

const fragmentShader = `
    uniform float uTime;
    uniform vec3 uColor1;
    uniform vec3 uColor2;
    uniform vec3 uColor3;

    varying vec2 vUv;
    varying float vDisplacement;

    void main() {
        // Create gradient based on displacement and UV
        float mixStrength = (vDisplacement + 0.5) * 0.5 + vUv.y * 0.3;
        mixStrength = clamp(mixStrength, 0.0, 1.0);

        vec3 color = mix(uColor1, uColor2, mixStrength);
        color = mix(color, uColor3, smoothstep(0.4, 0.8, mixStrength + sin(uTime * 0.5) * 0.1));

        // Fresnel-like edge glow
        float edge = pow(1.0 - abs(vDisplacement) * 0.5, 2.0);
        color += vec3(0.1, 0.3, 0.4) * edge * 0.3;

        // Subtle transparency variation
        float alpha = 0.85 + vDisplacement * 0.1;

        gl_FragColor = vec4(color, alpha);
    }
`;

// Create blob geometry
const geometry = new THREE.IcosahedronGeometry(2, 64);

const material = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
        uTime: { value: 0 },
        uMouseX: { value: 0 },
        uMouseY: { value: 0 },
        uDistortion: { value: 0.4 },
        uColor1: { value: new THREE.Color('#0a0a1a') },
        uColor2: { value: new THREE.Color('#1a3a4a') },
        uColor3: { value: new THREE.Color('#2a5a6a') },
    },
    transparent: true,
    side: THREE.DoubleSide,
});

const blob = new THREE.Mesh(geometry, material);
scene.add(blob);

// Add subtle wireframe overlay
const wireGeometry = new THREE.IcosahedronGeometry(2.01, 16);
const wireMaterial = new THREE.MeshBasicMaterial({
    color: '#64ffda',
    wireframe: true,
    transparent: true,
    opacity: 0.03,
});
const wireframe = new THREE.Mesh(wireGeometry, wireMaterial);
scene.add(wireframe);

// Add floating particles
const particlesGeometry = new THREE.BufferGeometry();
const particlesCount = 500;
const posArray = new Float32Array(particlesCount * 3);

for (let i = 0; i < particlesCount * 3; i++) {
    posArray[i] = (Math.random() - 0.5) * 15;
}

particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

const particlesMaterial = new THREE.PointsMaterial({
    size: 0.02,
    color: '#64ffda',
    transparent: true,
    opacity: 0.4,
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

    // Rotate blob slowly
    blob.rotation.x = time * 0.1 + mouse.y * 0.3;
    blob.rotation.y = time * 0.15 + mouse.x * 0.3;

    wireframe.rotation.x = blob.rotation.x;
    wireframe.rotation.y = blob.rotation.y;

    // Animate particles
    particles.rotation.y = time * 0.02;
    particles.rotation.x = time * 0.01;

    renderer.render(scene, camera);
}

// Handle resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
