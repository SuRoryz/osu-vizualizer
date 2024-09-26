#version 330 core

out vec4 FragColor;

// Uniforms
uniform float u_opacity;
uniform float u_time;

// Slider outline color (slightly darker than main slider)
const vec3 outline_color = vec3(0.6, 0.3, 0.0); // Darker orange

// Helper function to convert HSV to RGB
vec3 hsv2rgb(vec3 c)
{
    vec3 rgb = clamp(abs(mod(c.x * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
    return c.z * mix(vec3(1.0), rgb, c.y);
}

void main()
{
    // Calculate hue changing over time
    float hue = mod(u_time * 0.0001, 1.0);

    // Convert HSV to RGB
    vec3 color = hsv2rgb(vec3(hue, 1.0, 1.0));

    // Set color with specified opacity
    FragColor = vec4(color, u_opacity);
}
