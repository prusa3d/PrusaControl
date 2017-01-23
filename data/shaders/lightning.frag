#version 110


varying vec4 diffuse,ambientGlobal, ambient, ecPos;
varying vec3 normal,halfVector;

void main()
{
    vec3 n,halfV,viewV,lightDir;
    float NdotL,NdotHV;
    vec4 color = ambientGlobal;
    //vec4 color = vec4(0.05,0.05,0.05,1.);
    float att, dist;

    /* a fragment shader can't write a verying variable, hence we need
    a new variable to store the normalized interpolated normal */
    n = normalize(normal);

    // Compute the ligt direction
    lightDir = vec3(gl_LightSource[0].position-ecPos);

    /* compute the distance to the light source to a varying variable*/
    dist = length(lightDir);


    /* compute the dot product between normal and ldir */
    NdotL = max(dot(n,normalize(lightDir)),0.0);

    if (NdotL > 0.0) {

        att = 1.0 / (gl_LightSource[0].constantAttenuation +
                gl_LightSource[0].linearAttenuation * dist +
                gl_LightSource[0].quadraticAttenuation * dist * dist);
        color += att * (diffuse * NdotL + ambient);


        halfV = normalize(halfVector);
        NdotHV = max(dot(n,halfV),0.0);
        color += att * gl_FrontMaterial.specular * gl_LightSource[0].specular * pow(NdotHV,gl_FrontMaterial.shininess);
    }

    gl_FragColor = color;
    //gl_FragColor = vec4(1., 1., 1., 1.);
    //gl_FragColor.a = 1.;
}