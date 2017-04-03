#version 110

varying float object_z;

void main()
{
   vec3 normal, lightDir, viewVector, halfVector;
   vec4 diffuse, ambient, globalAmbient, specular = vec4(0.0);
   float NdotL,NdotHV;

   // First transform the normal into eye space and normalize the result.
   normal = normalize(gl_NormalMatrix * gl_Normal);

   // Now normalize the light's direction. Note that according to the OpenGL specification, the light is stored in eye space.
   // Also since we're talking about a directional light, the position field is actually direction.
   lightDir = normalize(vec3(gl_LightSource[0].position));

   // Compute the cos of the angle between the normal and lights direction. The light is directional so the direction is constant for every vertex.
   // Since these two are normalized the cosine is the dot product. We also need to clamp the result to the [0,1] range.
   NdotL = max(dot(normal, lightDir), 0.0);

   // Compute the diffuse, ambient and globalAmbient terms.
//    diffuse = NdotL * (gl_FrontMaterial.diffuse * gl_LightSource[0].diffuse);
//    ambient = gl_FrontMaterial.ambient * gl_LightSource[0].ambient;
   diffuse = NdotL * (gl_Color * gl_LightSource[0].diffuse);
   ambient = gl_Color * gl_LightSource[0].ambient;
   globalAmbient = gl_LightModel.ambient * gl_FrontMaterial.ambient;

   // compute the specular term if NdotL is  larger than zero
   if (NdotL > 0.0) {
       NdotHV = max(dot(normal, normalize(gl_LightSource[0].halfVector.xyz)),0.0);
       specular = gl_FrontMaterial.specular * gl_LightSource[0].specular * pow(NdotHV,gl_FrontMaterial.shininess);
   }

   // Perform the same lighting calculation for the 2nd light source.
   lightDir = normalize(vec3(gl_LightSource[1].position));
   NdotL = max(dot(normal, lightDir), 0.0);
//    diffuse += NdotL * (gl_FrontMaterial.diffuse * gl_LightSource[1].diffuse);
//    ambient += gl_FrontMaterial.ambient * gl_LightSource[1].ambient;
   diffuse += NdotL * (gl_Color * gl_LightSource[1].diffuse);
   ambient += gl_Color * gl_LightSource[1].ambient;

   // compute the specular term if NdotL is  larger than zero
   if (NdotL > 0.0) {
       NdotHV = max(dot(normal, normalize(gl_LightSource[1].halfVector.xyz)),0.0);
       specular += gl_FrontMaterial.specular * gl_LightSource[1].specular * pow(NdotHV,gl_FrontMaterial.shininess);
   }

   gl_FrontColor = globalAmbient + diffuse + ambient + specular;
   gl_FrontColor.a = 1.;

   gl_Position = ftransform();
   object_z = gl_Vertex.z / gl_Vertex.w;
}