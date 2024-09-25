#version 330 core

uniform float u_time;
uniform float u_opacity;
uniform float u_circle_size;

in vec2 v_position;
out vec4 frag_color;

// Helper function to convert HSV to RGB
vec3 hsv2rgb(vec3 c)
{
    vec3 rgb = clamp(abs(mod(c.x * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
    return c.z * mix(vec3(1.0), rgb, c.y);
}

void main()
{
    // Calculate distance from center
    float dist = length(v_position);

    // Discard fragments outside the circle
    if (dist > u_circle_size)
        discard;

    // Calculate hue changing over time
    float hue = mod(u_time * 0.0001, 1.0);

    // Convert HSV to RGB
    vec3 color = hsv2rgb(vec3(hue, 1.0, 1.0));

    // Set color with specified opacity
    frag_color = vec4(color, u_opacity);
}
