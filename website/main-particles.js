// Particle Grid / Node Network
import * as THREE from 'three';

const canvas = document.getElementById('bg');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// Mouse
const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
document.addEventListener('mousemove', (e) => {
    mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
});

// Particles
const particleCount = 150;
const particles = [];
const positions = new Float32Array(particleCount * 3);
const velocities = [];

for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 10;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 5;

    velocities.push({
        x: (Math.random() - 0.5) * 0.01,
        y: (Math.random() - 0.5) * 0.01,
        z: (Math.random() - 0.5) * 0.005,
    });

    particles.push({
        x: positions[i * 3],
        y: positions[i * 3 + 1],
        z: positions[i * 3 + 2],
    });
}

// Points geometry
const pointsGeometry = new THREE.BufferGeometry();
pointsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

const pointsMaterial = new THREE.PointsMaterial({
    size: 0.05,
    color: '#64ffda',
    transparent: true,
    opacity: 0.8,
    blending: THREE.AdditiveBlending,
});

const points = new THREE.Points(pointsGeometry, pointsMaterial);
scene.add(points);

// Lines
const lineMaterial = new THREE.LineBasicMaterial({
    color: '#64ffda',
    transparent: true,
    opacity: 0.15,
    blending: THREE.AdditiveBlending,
});

let linesMesh = null;
const maxDistance = 1.5;

function updateLines() {
    if (linesMesh) {
        scene.remove(linesMesh);
        linesMesh.geometry.dispose();
    }

    const linePositions = [];

    for (let i = 0; i < particleCount; i++) {
        for (let j = i + 1; j < particleCount; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dz = particles[i].z - particles[j].z;
            const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

            if (dist < maxDistance) {
                linePositions.push(particles[i].x, particles[i].y, particles[i].z);
                linePositions.push(particles[j].x, particles[j].y, particles[j].z);
            }
        }
    }

    if (linePositions.length > 0) {
        const linesGeometry = new THREE.BufferGeometry();
        linesGeometry.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
        linesMesh = new THREE.LineSegments(linesGeometry, lineMaterial);
        scene.add(linesMesh);
    }
}

camera.position.z = 5;

function animate() {
    requestAnimationFrame(animate);

    mouse.x += (mouse.targetX - mouse.x) * 0.05;
    mouse.y += (mouse.targetY - mouse.y) * 0.05;

    // Update particles
    const posAttr = pointsGeometry.attributes.position;

    for (let i = 0; i < particleCount; i++) {
        // Mouse repulsion
        const dx = particles[i].x - mouse.x * 3;
        const dy = particles[i].y - mouse.y * 3;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 2) {
            const force = (2 - dist) * 0.01;
            velocities[i].x += (dx / dist) * force;
            velocities[i].y += (dy / dist) * force;
        }

        // Apply velocity
        particles[i].x += velocities[i].x;
        particles[i].y += velocities[i].y;
        particles[i].z += velocities[i].z;

        // Damping
        velocities[i].x *= 0.99;
        velocities[i].y *= 0.99;
        velocities[i].z *= 0.99;

        // Boundaries
        if (particles[i].x > 5 || particles[i].x < -5) velocities[i].x *= -1;
        if (particles[i].y > 5 || particles[i].y < -5) velocities[i].y *= -1;
        if (particles[i].z > 2.5 || particles[i].z < -2.5) velocities[i].z *= -1;

        posAttr.array[i * 3] = particles[i].x;
        posAttr.array[i * 3 + 1] = particles[i].y;
        posAttr.array[i * 3 + 2] = particles[i].z;
    }

    posAttr.needsUpdate = true;
    updateLines();

    renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
