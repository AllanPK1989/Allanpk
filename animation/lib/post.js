// Post-processing chain: ambient occlusion + depth of field.
//
// Two things were missing that the eye notices immediately:
//
//  * Contact shading. Without AO, objects sit *on* the floor rather than *in*
//    the scene — no darkening in the crevices where a leg meets concrete, or
//    under a hopper cone. GTAO puts that back and is what makes geometry feel
//    seated.
//
//  * Focus. A pinhole camera renders the far wall as sharply as the operator,
//    which reads as CGI. A shallow depth of field tells the viewer where to
//    look and is most of what separates "render" from "footage".
//
// Focus distance is driven from the camera rig's own target each frame, so the
// subject of the shot is always what is sharp.

import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass }     from 'three/addons/postprocessing/RenderPass.js';
import { OutputPass }     from 'three/addons/postprocessing/OutputPass.js';
import { GTAOPass }       from 'three/addons/postprocessing/GTAOPass.js';
import { BokehPass }      from 'three/addons/postprocessing/BokehPass.js';

export function makePost(renderer, scene, camera, {
  width = window.innerWidth,
  height = window.innerHeight,
  ao = true,
  dof = true,
  aoScale = 0.5,        // AO is traced at half res; it is the expensive pass
  aperture = 0.0009,
  maxblur = 0.0034,
} = {}) {
  const composer = new EffectComposer(renderer);
  composer.setSize(width, height);
  composer.addPass(new RenderPass(scene, camera));

  let gtao = null;
  if (ao) {
    gtao = new GTAOPass(scene, camera, width * aoScale, height * aoScale);
    gtao.output = GTAOPass.OUTPUT.Default;
    // Radius is in world units: ~0.4 m catches the crevice where a machine leg
    // meets the floor without smearing shade across a whole wall panel.
    gtao.updateGtaoMaterial({
      radius: 0.4,
      distanceExponent: 1.2,
      thickness: 0.6,
      scale: 1.1,
      samples: 8,
      screenSpaceRadius: false,
    });
    gtao.updatePdMaterial({ lumaPhi: 8, depthPhi: 2, normalPhi: 4, radius: 3, samples: 8 });
    composer.addPass(gtao);
  }

  let bokeh = null;
  if (dof) {
    bokeh = new BokehPass(scene, camera, { focus: 8.0, aperture, maxblur });
    composer.addPass(bokeh);
  }

  composer.addPass(new OutputPass());

  return {
    composer,
    gtao,
    bokeh,
    /** Focus on a world-space point — normally the camera rig's target. */
    focusOn(point) {
      if (!bokeh) return;
      bokeh.uniforms.focus.value = Math.max(1.0, camera.position.distanceTo(point));
    },
    setSize(w, h) {
      composer.setSize(w, h);
      if (gtao) gtao.setSize(w * aoScale, h * aoScale);
    },
    dispose() { composer.dispose(); },
  };
}
