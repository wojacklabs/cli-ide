// Floating ASCII Cubes - Terminal + 3D
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

// ASCII characters
const asciiChars = '01{}[]<>/*-+=$#@&%!?:;~^'.split('');

// Create ASCII texture
function createASCIITexture(char) {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, 64, 64);

    ctx.font = 'bold 48px JetBrains Mono, monospace';
    ctx.fillStyle = '#64ffda';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(char, 32, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    return texture;
}

// Create cubes
const cubes = [];
const cubeCount = 25;

for (let i = 0; i < cubeCount; i++) {
    const size = 0.3 + Math.random() * 0.4;
    const geometry = new THREE.BoxGeometry(size, size, size);

    // Random ASCII char for each face
    const materials = [];
    for (let j = 0; j < 6; j++) {
        const char = asciiChars[Math.floor(Math.random() * asciiChars.length)];
        materials.push(new THREE.MeshBasicMaterial({
            map: createASCIITexture(char),
            transparent: true,
            opacity: 0.9,
        }));
    }

    const cube = new THREE.Mesh(geometry, materials);

    // Random position
    cube.position.x = (Math.random() - 0.5) * 10;
    cube.position.y = (Math.random() - 0.5) * 6;
    cube.position.z = (Math.random() - 0.5) * 5 - 2;

    // Random rotation speed
    cube.userData = {
        rotationSpeed: {
            x: (Math.random() - 0.5) * 0.02,
            y: (Math.random() - 0.5) * 0.02,
            z: (Math.random() - 0.5) * 0.01,
        },
        floatSpeed: Math.random() * 0.5 + 0.5,
        floatOffset: Math.random() * Math.PI * 2,
        originalY: cube.position.y,
    };

    // Add wireframe edges
    const edges = new THREE.EdgesGeometry(geometry);
    const line = new THREE.LineSegments(
        edges,
        new THREE.LineBasicMaterial({ color: '#64ffda', transparent: true, opacity: 0.3 })
    );
    cube.add(line);

    scene.add(cube);
    cubes.push(cube);
}

// Add ambient particles
const particlesGeometry = new THREE.BufferGeometry();
const particlesCount = 200;
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

// Add connecting lines between nearby cubes
const lineMaterial = new THREE.LineBasicMaterial({
    color: '#64ffda',
    transparent: true,
    opacity: 0.1,
});

let linesMesh = null;

function updateLines() {
    if (linesMesh) {
        scene.remove(linesMesh);
        linesMesh.geometry.dispose();
    }

    const linePositions = [];
    const maxDist = 3;

    for (let i = 0; i < cubes.length; i++) {
        for (let j = i + 1; j < cubes.length; j++) {
            const dist = cubes[i].position.distanceTo(cubes[j].position);
            if (dist < maxDist) {
                linePositions.push(
                    cubes[i].position.x, cubes[i].position.y, cubes[i].position.z,
                    cubes[j].position.x, cubes[j].position.y, cubes[j].position.z
                );
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

    const time = performance.now() * 0.001;

    mouse.x += (mouse.targetX - mouse.x) * 0.05;
    mouse.y += (mouse.targetY - mouse.y) * 0.05;

    // Update cubes
    cubes.forEach((cube) => {
        const { rotationSpeed, floatSpeed, floatOffset, originalY } = cube.userData;

        // Rotate
        cube.rotation.x += rotationSpeed.x;
        cube.rotation.y += rotationSpeed.y;
        cube.rotation.z += rotationSpeed.z;

        // Float up and down
        cube.position.y = originalY + Math.sin(time * floatSpeed + floatOffset) * 0.3;
    });

    // Camera follows mouse slightly
    camera.position.x = mouse.x * 0.5;
    camera.position.y = mouse.y * 0.3;
    camera.lookAt(0, 0, 0);

    // Update connecting lines
    updateLines();

    // Rotate particles
    particles.rotation.y = time * 0.02;

    renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
