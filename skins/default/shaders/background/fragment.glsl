#version 330 core

// Shadertoy Uniforms
uniform vec3 iResolution;    // viewport resolution (in pixels)
uniform float iTime;         // shader playback time (in seconds)
uniform float iLastPressTime;

in vec2 v_tex_coord;
out vec4 frag_color;

void mainImage( out vec4 O, vec2 u )
{
    vec2 R =  iResolution.xy,
         U = ( u+u - R ) / R.y, P;  
    U.x += sin(U.y + iTime) * .1;
    O*=0.;
    for (float i,l; i < 19.; i++ )
        l = length( P = 13.* ( U + i/20.* cos(i+iTime +vec2(0,11)) ) *  mat2(cos( i+i + vec4(0,33,11,0)))),
        R = P*P,
        O +=   (1. - l       ) / abs(P.x * P.y) / 1e3 
             + (1. - l * 1.86) / abs(R.x - R.y) / 1e2  
             + .1 / (l - .01);    
}

void main()
{
    vec4 color;
    mainImage(color, gl_FragCoord.xy);
    frag_color = color * 1;
}