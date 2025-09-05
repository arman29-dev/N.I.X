window.onload = function() {
    // 3D Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('hero-canvas'), alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);

    // Create a custom geometric shape for the nodes/particles
    const geometry = new THREE.DodecahedronGeometry(0.5);
    const material = new THREE.MeshBasicMaterial({ color: 0x3df5f5, wireframe: true });

    // Particles for the network effect
    const particles = [];
    const particleCount = 200;
    for (let i = 0; i < particleCount; i++) {
        const particle = new THREE.Mesh(geometry, material);
        particle.position.x = (Math.random() - 0.5) * 50;
        particle.position.y = (Math.random() - 0.5) * 50;
        particle.position.z = (Math.random() - 0.5) * 50;
        particle.userData.velocity = new THREE.Vector3(
            (Math.random() - 0.5) * 0.05,
            (Math.random() - 0.5) * 0.05,
            (Math.random() - 0.5) * 0.05
        );
        scene.add(particle);
        particles.push(particle);
    }

    camera.position.z = 25;

    // Animation loop
    const animate = function() {
        requestAnimationFrame(animate);

        particles.forEach(p => {
            p.rotation.x += p.userData.velocity.x * 0.1;
            p.rotation.y += p.userData.velocity.y * 0.1;
            p.position.add(p.userData.velocity);

            // Wrap particles around the screen
            if (p.position.x > 25 || p.position.x < -25) p.userData.velocity.x *= -1;
            if (p.position.y > 25 || p.position.y < -25) p.userData.velocity.y *= -1;
            if (p.position.z > 25 || p.position.z < -25) p.userData.velocity.z *= -1;
        });

        renderer.render(scene, camera);
    };

    animate();

    // Handle window resizing
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
};
