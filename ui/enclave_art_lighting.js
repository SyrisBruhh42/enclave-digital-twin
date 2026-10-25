/**
 * Enclave of the 16 — 2.5D Artistic Atmosphere, Dynamic Lighting, Micro-Life & Diorama Polish Engine
 * (`EnclaveArtLighting` v1.1.0)
 *
 * Zero-dependency, 60fps Canvas 2D artistic rendering engine inspired by Octopath Traveler HD-2D,
 * Eastward, Sea of Stars, Cozy Grove, and Animal Crossing: New Horizons.
 *
 * Reuses & Folds In Canonical LFS Suite Assets:
 * 1. `governance/lds-tokens.w3c.json` — Canonical 4-Theme W3C Palettes (`evergreen-dark`,
 *    `evergreen-light`, `high-contrast`, `calm`) & `LDS-CONFLICT-01..06` tokens.
 * 2. `capsules/crucible-automata` — 4 Aegis Hearth Elemental Visual Motifs:
 *    - `PorchHearth` ("The Porch Hearth" — rising warm embers condensing into starlight dew)
 *    - `RainGarden` ("Mossling's Rain Garden" — cascading terraced spring water & crystal flora)
 *    - `FlowHourglass` ("The Hourglass of Flow" — mass-conserving golden sand focus stream)
 *    - `AlchemicalForge` ("The Alchemist's Crucible" — molten ore smelting & aether crystal arcs)
 * 3. `capsules/enclave-digital-twin/engine/{chronosphere,magneto_weather}.py` — Canonical orbital
 *    and magneto-meteorological parameters (`kp_exo`, `luna_alpha_phase`, `luna_beta_phase`,
 *    `luna_gamma_phase`, `ferrofluid_sea_surge_index`, `spore_luminescence_density`,
 *    `geode_charge_capacity_pct`, `micro_climate_regime`).
 *
 * Dual-compatible browser global (`window.EnclaveArtLighting`) and CommonJS/ESM bridge.
 * Strict ZT-9 Comfort (`reducedMotion`) compliant.
 */
(function (root, factory) {
  const api = factory();
  if (typeof window !== 'undefined') {
    window.EnclaveArtLighting = api;
  }
  if (typeof globalThis !== 'undefined') {
    globalThis.EnclaveArtLighting = api;
  }
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
    module.exports.EnclaveArtLighting = api;
    module.exports.default = api;
  } else if (root && typeof root === 'object') {
    root.EnclaveArtLighting = api;
  }
})(
  typeof globalThis !== 'undefined'
    ? globalThis
    : typeof self !== 'undefined'
      ? self
      : this,
  function () {
    'use strict';

    const DAY_PHASES = Object.freeze([
      'DAWN_SHIFT',
      'MIDDAY_EXPEDITION',
      'DUSK_CRAFT',
      'THE_FEAST'
    ]);

    /**
     * Canonical Lewis Design System (LDS) 4-Pack Palettes folded directly from
     * `governance/lds-tokens.w3c.json` (`LDS-CONFLICT-01..06`).
     */
    const LDS_W3C_THEME_PACKS = Object.freeze({
      'evergreen-dark': Object.freeze({
        bgCanvas: '#0F1714',
        bgSurface: '#141F1B',
        bgElevated: '#1B2924',
        textPrimary: '#ECF4F0',
        textSecondary: '#B6C9BF',
        textMuted: '#96ADA2',
        accentPrimary: '#6EE7B7',
        accentSecondary: '#72C9D4',
        statusSuccess: '#4ADE80',
        statusWarning: '#FACC15',
        statusDanger: '#F87171',
        statusInfo: '#60A5FA',
        borderDefault: '#2A3C35',
        borderFocus: '#6EE7B7'
      }),
      'evergreen-light': Object.freeze({
        bgCanvas: '#F6FAF8',
        bgSurface: '#FFFFFF',
        bgElevated: '#EBF3EE',
        textPrimary: '#0F1D17',
        textSecondary: '#284237',
        textMuted: '#3D5A4E',
        accentPrimary: '#165B36',
        accentSecondary: '#0E5866',
        statusSuccess: '#145E32',
        statusWarning: '#784506',
        statusDanger: '#991B1B',
        statusInfo: '#1E40AF',
        borderDefault: '#B8CCC2',
        borderFocus: '#165B36'
      }),
      'high-contrast': Object.freeze({
        bgCanvas: '#000000',
        bgSurface: '#000000',
        bgElevated: '#0A0A0A',
        textPrimary: '#FFFFFF',
        textSecondary: '#FFFF00',
        textMuted: '#E0F2FE',
        accentPrimary: '#00FFFF',
        accentSecondary: '#FFE600',
        statusSuccess: '#4ADE80',
        statusWarning: '#FFE600',
        statusDanger: '#FF8A8A',
        statusInfo: '#7DD3FC',
        borderDefault: '#FFFFFF',
        borderFocus: '#00FFFF'
      }),
      calm: Object.freeze({
        bgCanvas: '#0B1113',
        bgSurface: '#101719',
        bgElevated: '#162023',
        textPrimary: '#EDF2ED',
        textSecondary: '#C2D0CD',
        textMuted: '#A0AFAC',
        accentPrimary: '#B8E4CF',
        accentSecondary: '#72C9D4',
        statusSuccess: '#9BD8B9',
        statusWarning: '#E6C875',
        statusDanger: '#E58E8E',
        statusInfo: '#89C4E1',
        borderDefault: '#273335',
        borderFocus: '#B8E4CF'
      })
    });

    /**
     * Canonical 4 Aegis Hearth Elemental Visual Motifs folded from
     * `capsules/crucible-automata/crates/automata-types/src/lib.rs` (`SanctuaryScene`).
     */
    const AEGIS_HEARTH_MOTIFS = Object.freeze({
      PorchHearth: Object.freeze({
        id: 'PorchHearth',
        slug: 'hearth',
        title: 'The Porch Hearth',
        whisper:
          'Warm embers rise through the stone hearth, breathing gentle heat into the evening air while steam condenses into starlight dew above.',
        primaryColor: '#fb923c',
        secondaryColor: '#fde047',
        dewColor: '#7dd3fc'
      }),
      RainGarden: Object.freeze({
        id: 'RainGarden',
        slug: 'garden',
        title: "Mossling's Rain Garden",
        whisper:
          'Spring water cascades down terraced moss-stone pools, nourishing glowing starlight flora in harmony with your Aegis Familiar.',
        primaryColor: '#34d399',
        secondaryColor: '#38bdf8',
        crystalColor: '#a7f3d0'
      }),
      FlowHourglass: Object.freeze({
        id: 'FlowHourglass',
        slug: 'hourglass',
        title: 'The Hourglass of Flow',
        whisper:
          'Every grain of golden sand is physically conserved as it trickles through the carved stone aperture—a quiet companion for focus and rest.',
        primaryColor: '#facc15',
        secondaryColor: '#c084fc',
        sandColor: '#fde68a'
      }),
      AlchemistCrucible: Object.freeze({
        id: 'AlchemistCrucible',
        slug: 'forge',
        title: "The Alchemist's Crucible",
        whisper:
          'Interactive elemental workshop: smelt iron ore into ingots, combine acid with starlight crystals, or test your sanctuary guardians.',
        primaryColor: '#32f5c8',
        secondaryColor: '#f97316',
        plasmaColor: '#e879f9'
      })
    });

    /**
     * Micro-climate regimes from `enclave-digital-twin/engine/magneto_weather.py`.
     */
    const MICRO_CLIMATE_REGIMES = Object.freeze([
      'Bifurcated_Thermal_Shear',
      'Ferrofluid_Tidal_Squall',
      'Lightning_Geode_Supercharge',
      'Bioluminescent_Spore_Calm',
      'Magnetic_Null_Aurora'
    ]);

    const SQUAD_RIM_COLORS = Object.freeze({
      'The Forge': '#fb923c',
      'The Wilds': '#34d399',
      'The Mind': '#c084fc',
      'The Hub': '#fbbf24'
    });

    const TOOL_ICONS = Object.freeze({
      trowel: '⚗️',
      alchemical_trowel: '⚗️',
      bug_net: '🦋',
      silk_bug_net: '🦋',
      dip_rod: '🎣',
      ferro_dip_rod: '🎣',
      watering_can: '💧',
      chelated_watering_can: '💧',
      tinker_wrench: '🪑',
      resonance_tuning_fork: '🪑',
      gift_satchel: '🎁',
      lantern_satchel: '🎁'
    });

    const BIOME_TINTS = Object.freeze({
      crater_valley: {
        cellName: 'Enclave_Crater_Valley',
        waterDeep: '#0c3b49',
        waterMid: '#116979',
        waterHighlight: '#32f5c8',
        waterSecondary: '#38d6ff',
        sporeColor: '#32f5c8',
        floraAccent: '#ffd866',
        mistTint: [168, 230, 207]
      },
      storm_ridge: {
        cellName: 'Basalt_Spire_Ridge',
        waterDeep: '#0c233b',
        waterMid: '#0369a1',
        waterHighlight: '#7dd3fc',
        waterSecondary: '#38bdf8',
        sporeColor: '#60a5fa',
        floraAccent: '#bae6fd',
        mistTint: [148, 197, 248]
      },
      genesis_terraces: {
        cellName: 'Ferrofluid_Tidal_Basin',
        waterDeep: '#09382e',
        waterMid: '#059669',
        waterHighlight: '#6ee7b7',
        waterSecondary: '#fde047',
        sporeColor: '#fde047',
        floraAccent: '#f59e0b',
        mistTint: [210, 240, 180]
      },
      spore_glade: {
        cellName: 'Mycelial_Geode_Caverns',
        waterDeep: '#241242',
        waterMid: '#5b21b6',
        waterHighlight: '#e879f9',
        waterSecondary: '#c084fc',
        sporeColor: '#e879f9',
        floraAccent: '#38f5d4',
        mistTint: [216, 180, 254]
      },
      forge_caldera: {
        cellName: 'Shattered_Magnetite_Steppe',
        waterDeep: '#33140c',
        waterMid: '#9a3412',
        waterHighlight: '#fb923c',
        waterSecondary: '#fde047',
        sporeColor: '#fb923c',
        floraAccent: '#f97316',
        mistTint: [251, 169, 116]
      }
    });

    function hash2D(x, y, seed = 0) {
      const n = Math.sin(x * 127.1 + y * 311.7 + seed * 74.7) * 43758.5453123;
      return n - Math.floor(n);
    }

    function clamp(val, min, max) {
      return Math.max(min, Math.min(max, val));
    }

    function rgba(r, g, b, a) {
      return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${Number(clamp(a, 0, 1)).toFixed(3)})`;
    }

    /**
     * Resolves active Lewis Design System theme pack and ZT-9 comfort flags.
     */
    function resolveComfortAndTheme(world, options) {
      const docTheme =
        typeof document !== 'undefined' && document.documentElement
          ? document.documentElement.getAttribute('data-theme')
          : null;
      const rawTheme =
        options?.theme ||
        world?.theme ||
        docTheme ||
        'evergreen-dark';
      const theme = LDS_W3C_THEME_PACKS[rawTheme] ? rawTheme : 'evergreen-dark';
      const ldsTokens = LDS_W3C_THEME_PACKS[theme];

      let reducedMotion = false;
      if (typeof options?.reducedMotion === 'boolean') {
        reducedMotion = options.reducedMotion;
      } else if (typeof world?.reducedMotion === 'boolean') {
        reducedMotion = world.reducedMotion;
      } else if (typeof world?.comfort?.reduced_motion === 'boolean') {
        reducedMotion = world.comfort.reduced_motion;
      } else if (
        typeof window !== 'undefined' &&
        typeof window.matchMedia === 'function' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches
      ) {
        reducedMotion = true;
      }

      return {
        theme,
        ldsTokens,
        reducedMotion,
        isHighContrast: theme === 'high-contrast',
        isLightTheme: theme === 'evergreen-light',
        isCalmTheme: theme === 'calm'
      };
    }

    /**
     * Resolves which of the 4 `crucible-automata` Aegis Hearth elemental motifs
     * belongs to a given Enclave building or landmark.
     */
    function resolveBuildingHearthMotif(building) {
      const id = String(building?.id || '').toLowerCase();
      const squad = String(building?.squad || '');
      if (id.includes('hearth') || id.includes('banquet') || id.includes('proj_08') || id.includes('lodge')) {
        return AEGIS_HEARTH_MOTIFS.PorchHearth;
      }
      if (id.includes('genesis') || id.includes('sanctuary') || id.includes('menagerie') || id.includes('proj_04') || id.includes('proj_03') || id.includes('nook')) {
        return AEGIS_HEARTH_MOTIFS.RainGarden;
      }
      if (id.includes('simulacrum') || id.includes('lyceum') || id.includes('atlas') || id.includes('amphitheater') || squad === 'The Mind') {
        return AEGIS_HEARTH_MOTIFS.FlowHourglass;
      }
      return AEGIS_HEARTH_MOTIFS.AlchemistCrucible;
    }

    /**
     * Normalizes disparate world state formats (`enclave_city.html` vs `enclave-city-app.mjs`)
     * into a unified view for all rendering passes.
     */
    function normalizeWorldContext(ctx, world, camera, animTick, options) {
      const wObj = world && typeof world === 'object' ? world : {};
      const opts = options && typeof options === 'object' ? options : {};
      const cam =
        camera && typeof camera === 'object'
          ? camera
          : wObj.camera && typeof wObj.camera === 'object'
            ? wObj.camera
            : { x: 24, y: 24, zoom: 1.0 };

      const canvasW = opts.width || ctx?.canvas?.width || 960;
      const canvasH = opts.height || ctx?.canvas?.height || 640;

      const zoom = Number.isFinite(Number(cam.zoom)) ? Number(cam.zoom) : 1.0;
      const baseTileSize = Number.isFinite(Number(opts.baseTileSize))
        ? Number(opts.baseTileSize)
        : Number.isFinite(Number(wObj.tileSize))
          ? Number(wObj.tileSize)
          : wObj.townMap || wObj.dayPhase
            ? 22
            : 28;
      const scale = Number.isFinite(Number(opts.scale))
        ? Number(opts.scale)
        : Number.isFinite(Number(opts.tileSize))
          ? Number(opts.tileSize)
          : Math.max(8, baseTileSize * zoom);

      const camX = Number.isFinite(Number(cam.x)) ? Number(cam.x) : 24;
      const camY = Number.isFinite(Number(cam.y)) ? Number(cam.y) : 24;
      const offsetX = Number.isFinite(Number(opts.offsetX))
        ? Number(opts.offsetX)
        : Number.isFinite(Number(opts.originX))
          ? Number(opts.originX)
          : canvasW / 2 - camX * scale;
      const offsetY = Number.isFinite(Number(opts.offsetY))
        ? Number(opts.offsetY)
        : Number.isFinite(Number(opts.originY))
          ? Number(opts.originY)
          : canvasH / 2 - camY * scale;

      const dayPhase =
        opts.dayPhase ||
        wObj.dayPhase ||
        DAY_PHASES[wObj.phaseIdx ?? 0] ||
        'DAWN_SHIFT';

      const kpExo = Number.isFinite(Number(opts.kpExo))
        ? Number(opts.kpExo)
        : Number.isFinite(Number(wObj.kpExo ?? wObj.kp_exo))
          ? Number(wObj.kpExo ?? wObj.kp_exo)
          : 3.8;

      const biomeId =
        opts.biomeId ||
        wObj.biomeId ||
        wObj.biome?.id ||
        wObj.townMap?.biome?.id ||
        'crater_valley';

      const comfort = resolveComfortAndTheme(wObj, opts);
      const rawTick = Number.isFinite(Number(animTick)) ? Number(animTick) : 0;
      const timeSec = comfort.reducedMotion
        ? 0
        : rawTick > 50000
          ? rawTick * 0.001
          : rawTick / 60;

      const grid = opts.grid || wObj.grid || wObj.townMap?.grid || [];
      const gridH = Array.isArray(grid) ? grid.length : 0;
      const gridW = gridH > 0 && Array.isArray(grid[0]) ? grid[0].length : 0;

      const rawBuildings =
        opts.buildings ||
        wObj.buildings ||
        wObj.townMap?.buildings ||
        (typeof window !== 'undefined' && Array.isArray(window.BUILDINGS)
          ? window.BUILDINGS
          : []);

      const buildings = Array.isArray(rawBuildings)
        ? rawBuildings.map(b => ({
            id: b.id || '',
            name: b.name || '',
            category: b.category || 'grand_project',
            squad: b.squad || 'The Hub',
            x: Number(b.x ?? 0),
            y: Number(b.y ?? 0),
            w: Number(b.w ?? 4),
            d: Number(b.d ?? b.h ?? 4),
            h: Number(b.h ?? (b.stories ? b.stories * 1.3 : 3)),
            stories: Number(b.stories ?? b.h ?? 2),
            wall: b.wall || b.wallColor || '#546875',
            roof: b.roof || b.roofColor || '#2f9fb8',
            trim: b.trim || b.trimColor || '#32f5c8',
            icon: b.icon || '🏛️',
            progress: Number(b.progress ?? 100),
            motif: resolveBuildingHearthMotif(b)
          }))
        : [];

      let rawCitizens = opts.citizens || wObj.citizens || [];
      if (
        (!Array.isArray(rawCitizens) || rawCitizens.length === 0) &&
        Array.isArray(opts.citizenProfiles) &&
        opts.citizenRuntime instanceof Map
      ) {
        rawCitizens = opts.citizenProfiles.map(p => {
          const rt = opts.citizenRuntime.get(p.characterId) || {};
          return { ...p, ...rt };
        });
      } else if (
        (!Array.isArray(rawCitizens) || rawCitizens.length === 0) &&
        wObj.willow
      ) {
        rawCitizens = [
          {
            id: 'enclave_07_willow',
            name: 'Willow',
            squad: 'The Wilds',
            x: wObj.willow.x,
            y: wObj.willow.y,
            shirt: '#1abc9c',
            icon: '⚗️',
            polarity: 'Libra (The Aesthete)'
          }
        ];
      }

      const citizens = Array.isArray(rawCitizens)
        ? rawCitizens.map((c, idx) => {
            const cid = c.id || c.characterId || `citizen_${idx}`;
            const speechBubble = opts.speechBubble || wObj.speechBubble;
            const bubbleFromGlobal =
              speechBubble &&
              speechBubble.characterId === cid &&
              (!speechBubble.until || rawTick < speechBubble.until)
                ? speechBubble.text
                : '';
            return {
              id: cid,
              name: c.name || 'Villager',
              epithet: c.epithet || '',
              squad: c.squad || 'The Wilds',
              x: Number(c.x ?? c.homeX ?? 22),
              y: Number(c.y ?? c.homeY ?? 22),
              targetX: Number(c.targetX ?? c.x ?? 22),
              targetY: Number(c.targetY ?? c.y ?? 22),
              walkPhase: Number(c.walkPhase ?? c.phaseOffset ?? idx * 0.7),
              shirt: c.shirt || c.voxelColors?.tunic || '#1abc9c',
              skin: c.skin || c.voxelColors?.skin || '#f5cba7',
              hat: c.hat || c.voxelColors?.hat || '#d97706',
              accent: c.accent || c.voxelColors?.accent || '#32f5c8',
              icon: c.icon || '✨',
              polarity: c.polarity || c.ironicStarSign || 'Libra (The Aesthete)',
              stress: Number(c.stress ?? 0.2),
              bond: Number(c.bond ?? c.initialBond ?? 0.85),
              bubbleText:
                c.bubbleTimer > 0 && c.bubbleText
                  ? c.bubbleText
                  : bubbleFromGlobal || '',
              raw: c
            };
          })
        : [];

      const trees = opts.trees || wObj.trees || wObj.townMap?.trees || [];
      const resourceNodes =
        opts.resourceNodes ||
        wObj.resourceNodes ||
        wObj.interactiveNodes ||
        wObj.townMap?.interactiveNodes ||
        [];
      const decorations =
        opts.decorations ||
        wObj.decorations ||
        wObj.placedDecorations ||
        [];
      const geodeObelisk =
        opts.geodeObelisk ||
        wObj.geodeObelisk ||
        wObj.townMap?.geodeObelisk ||
        { x: 23, y: 21 };

      const equippedToolId =
        opts.equippedToolId ||
        wObj.equippedToolId ||
        wObj.activeToolId ||
        'trowel';

      const atmos = computeAtmosphericState(
        opts.timeOfDay ?? wObj.timeOfDay ?? null,
        kpExo,
        biomeId,
        dayPhase,
        {
          ...opts,
          sol: wObj.sol ?? wObj.colony_sol ?? 1,
          lunaAlphaPhase: wObj.luna_alpha_phase ?? opts.luna_alpha_phase,
          lunaBetaPhase: wObj.luna_beta_phase ?? opts.luna_beta_phase,
          lunaGammaPhase: wObj.luna_gamma_phase ?? opts.luna_gamma_phase,
          ferrofluidSeaSurgeIndex:
            wObj.ferrofluid_sea_surge_index ?? opts.ferrofluid_sea_surge_index,
          sporeLuminescenceDensity:
            wObj.spore_luminescence_density ?? opts.spore_luminescence_density
        }
      );

      return {
        canvasW,
        canvasH,
        camX,
        camY,
        zoom,
        scale,
        offsetX,
        offsetY,
        dayPhase,
        kpExo,
        biomeId,
        biomeTint: BIOME_TINTS[biomeId] || BIOME_TINTS.crater_valley,
        comfort,
        rawTick,
        timeSec,
        grid,
        gridW,
        gridH,
        buildings,
        citizens,
        trees,
        resourceNodes,
        decorations,
        geodeObelisk,
        equippedToolId,
        atmos,
        options: opts
      };
    }

    function getCellType(grid, x, y) {
      if (!grid || y < 0 || y >= grid.length) return 'grass';
      const row = grid[y];
      if (!row || x < 0 || x >= row.length) return 'grass';
      const cell = row[x];
      if (!cell) return 'grass';
      if (typeof cell === 'string') return cell;
      if (typeof cell === 'object' && cell.type) return cell.type;
      return 'grass';
    }

    function isWaterCell(type) {
      return type === 'water' || type === 'river';
    }

    // =========================================================================
    // 1. MULTI-STOP TWIN-SUN & TRIPLE-MOON ATMOSPHERIC COLOR GRADING
    //    (Reusing `chronosphere.py` & `magneto_weather.py` Orbital/Tidal Math)
    // =========================================================================

    /**
     * Computes multi-stop atmospheric color grading, directional shadow vectors,
     * twin-sun / triple-moon orbital geometry, `ferrofluid_sea_surge_index`,
     * `spore_luminescence_density`, `geode_charge_capacity_pct`, and geomagnetic aurora state.
     */
    function computeAtmosphericState(
      timeOfDay,
      kpExo = 3.8,
      biomeId = 'crater_valley',
      dayPhase = 'DAWN_SHIFT',
      options = {}
    ) {
      if (timeOfDay && typeof timeOfDay === 'object') {
        const w = timeOfDay;
        const opt = kpExo && typeof kpExo === 'object' ? kpExo : {};
        const resolvedPhase =
          w.dayPhase || w.day_phase || DAY_PHASES[w.phaseIdx ?? 0] || 'DAWN_SHIFT';
        return computeAtmosphericState(
          w.timeOfDay ?? null,
          w.kpExo ?? w.kp_exo ?? 3.8,
          w.biomeId || w.biome?.id || 'crater_valley',
          resolvedPhase,
          {
            ...opt,
            sol: w.sol ?? w.colony_sol ?? 1,
            lunaAlphaPhase:
              w.luna_alpha_phase ?? w.triple_moon_tidal_vector?.luna_alpha_phase,
            lunaBetaPhase:
              w.luna_beta_phase ?? w.triple_moon_tidal_vector?.luna_beta_phase,
            lunaGammaPhase:
              w.luna_gamma_phase ?? w.triple_moon_tidal_vector?.luna_gamma_phase,
            ferrofluidSeaSurgeIndex:
              w.ferrofluid_sea_surge_index ??
              w.triple_moon_tidal_vector?.ferrofluid_sea_surge_index,
            sporeLuminescenceDensity: w.spore_luminescence_density
          }
        );
      }

      const resolvedPhase = DAY_PHASES.includes(dayPhase)
        ? dayPhase
        : 'DAWN_SHIFT';
      const kp = Number.isFinite(Number(kpExo)) ? clamp(Number(kpExo), 1.0, 9.0) : 3.8;
      const kpNorm = (kp - 1.0) / 8.0;
      const bId = BIOME_TINTS[biomeId] ? biomeId : 'crater_valley';
      const bTint = BIOME_TINTS[bId];
      const comfort = resolveComfortAndTheme(null, options);
      const sol = Number.isFinite(Number(options?.sol)) ? Math.max(1, Number(options.sol)) : 1;
      const phaseIdx = Math.max(0, DAY_PHASES.indexOf(resolvedPhase));
      const tickId = (sol - 1) * 4 + phaseIdx + 1;

      const defaultHours = {
        DAWN_SHIFT: 7.25,         // 05:30–09:00
        MIDDAY_EXPEDITION: 12.75, // 09:00–16:30
        DUSK_CRAFT: 18.25,        // 16:30–20:00
        THE_FEAST: 22.5           // 20:00–05:30
      };

      let hour = defaultHours[resolvedPhase] ?? 12.0;
      if (Number.isFinite(Number(timeOfDay)) && timeOfDay !== null) {
        const num = Number(timeOfDay);
        hour = num <= 1.0 && num >= 0 ? num * 24 : ((num % 24) + 24) % 24;
      }

      // Canonical `chronosphere.py` Triple Moon synodic phases & ferrofluid_sea_surge_index
      const lunaAlphaPhase = Number.isFinite(Number(options?.lunaAlphaPhase))
        ? clamp(Number(options.lunaAlphaPhase), 0, 1)
        : Number(((0.21 + tickId * 0.142857) % 1.0).toFixed(4));
      const lunaBetaPhase = Number.isFinite(Number(options?.lunaBetaPhase))
        ? clamp(Number(options.lunaBetaPhase), 0, 1)
        : Number(((0.54 + tickId * 0.083333) % 1.0).toFixed(4));
      const lunaGammaPhase = Number.isFinite(Number(options?.lunaGammaPhase))
        ? clamp(Number(options.lunaGammaPhase), 0, 1)
        : Number(((0.79 + tickId * 0.045455) % 1.0).toFixed(4));

      const tidalPull =
        0.40 * (0.5 * (1.0 + Math.cos(2.0 * Math.PI * lunaAlphaPhase))) +
        0.35 * (0.5 * (1.0 + Math.cos(2.0 * Math.PI * lunaBetaPhase))) +
        0.25 * (0.5 * (1.0 + Math.cos(2.0 * Math.PI * lunaGammaPhase)));

      const ferrofluidSeaSurgeIndex = Number.isFinite(Number(options?.ferrofluidSeaSurgeIndex))
        ? clamp(Number(options.ferrofluidSeaSurgeIndex), 0, 1)
        : Number(clamp(0.65 * tidalPull + 0.35 * kpNorm, 0, 1).toFixed(4));

      // Canonical `magneto_weather.py` spore_luminescence_density, geode_charge_capacity_pct & micro_climate_regime
      const nocturnalBoost =
        resolvedPhase === 'DUSK_CRAFT' || resolvedPhase === 'THE_FEAST' ? 0.22 : 0.0;
      const sporeLuminescenceDensity = Number.isFinite(Number(options?.sporeLuminescenceDensity))
        ? clamp(Number(options.sporeLuminescenceDensity), 0, 1)
        : Number(clamp(0.35 + nocturnalBoost + 0.40 * hash2D(sol, phaseIdx, 19), 0, 1).toFixed(3));

      const geodeChargeCapacityPct = Number(
        clamp(32.0 + 62.0 * kpNorm, 0, 100).toFixed(1)
      );

      let microClimateRegime = 'Bifurcated_Thermal_Shear';
      if (kp >= 7.2) {
        microClimateRegime = 'Lightning_Geode_Supercharge';
      } else if (kp <= 2.4) {
        microClimateRegime = 'Bioluminescent_Spore_Calm';
      } else if (kp >= 5.0) {
        microClimateRegime = 'Magnetic_Null_Aurora';
      } else if (ferrofluidSeaSurgeIndex >= 0.62) {
        microClimateRegime = 'Ferrofluid_Tidal_Squall';
      }

      // Phase-specific canonical artistic profiles
      let profile;
      if (resolvedPhase === 'DAWN_SHIFT') {
        profile = {
          phaseLabel: 'Dawn Shift (05:30–09:00)',
          skyTop: 'rgba(42, 28, 64, 0.24)',
          skyMid: 'rgba(214, 114, 122, 0.16)',
          skyHorizon: 'rgba(255, 190, 134, 0.22)',
          ambientTint: 'rgba(255, 196, 150, 0.10)',
          groundMistColor: 'rgba(226, 178, 214, 0.16)',
          shadowAngle: -0.78, // Long westward directional shadows
          shadowDx: -1.15,
          shadowDy: 0.48,
          shadowLength: 1.65,
          shadowAlpha: 0.34,
          shadowColor: 'rgba(28, 18, 44, 0.34)',
          sunRimColor: '#ffcf96',
          secondaryRimColor: '#a8f0ff',
          godRayColor: 'rgba(255, 204, 148, 0.14)',
          godRayAngle: 0.52,
          godRayAlpha: 0.85,
          lanternIntensity: 0.28,
          windowSpillIntensity: 0.24,
          bioIntensity: clamp(sporeLuminescenceDensity * 0.72, 0.25, 0.65),
          cloudShadowAlpha: 0.06,
          vignetteColor: 'rgba(18, 12, 30, 0.36)',
          vignetteAlpha: 0.36,
          bloomIntensity: 0.45
        };
      } else if (resolvedPhase === 'MIDDAY_EXPEDITION') {
        profile = {
          phaseLabel: 'Midday Expedition (09:00–16:30)',
          skyTop: 'rgba(56, 189, 248, 0.08)',
          skyMid: 'rgba(224, 251, 255, 0.05)',
          skyHorizon: 'rgba(255, 232, 186, 0.08)',
          ambientTint: 'rgba(230, 252, 255, 0.06)',
          groundMistColor: rgba(
            bTint.mistTint[0],
            bTint.mistTint[1],
            bTint.mistTint[2],
            0.06
          ),
          shadowAngle: 0.24,
          shadowDx: 0.35,
          shadowDy: 0.42,
          shadowLength: 0.65,
          shadowAlpha: 0.27,
          shadowColor: 'rgba(10, 24, 30, 0.27)',
          sunRimColor: '#e8fcff',
          secondaryRimColor: '#ffd89b',
          godRayColor: 'rgba(216, 248, 255, 0.11)',
          godRayAngle: 0.28,
          godRayAlpha: 0.65,
          lanternIntensity: 0.08,
          windowSpillIntensity: 0.05,
          bioIntensity: clamp(sporeLuminescenceDensity * 0.5, 0.18, 0.45),
          cloudShadowAlpha: 0.13,
          vignetteColor: 'rgba(6, 18, 16, 0.24)',
          vignetteAlpha: 0.24,
          bloomIntensity: 0.32
        };
      } else if (resolvedPhase === 'DUSK_CRAFT') {
        profile = {
          phaseLabel: 'Dusk Craft (16:30–20:00)',
          skyTop: 'rgba(38, 18, 62, 0.30)',
          skyMid: 'rgba(158, 62, 108, 0.20)',
          skyHorizon: 'rgba(242, 122, 62, 0.24)',
          ambientTint: 'rgba(232, 128, 78, 0.13)',
          groundMistColor: 'rgba(182, 118, 168, 0.14)',
          shadowAngle: 0.86, // Lengthening eastward shadows
          shadowDx: 1.25,
          shadowDy: 0.52,
          shadowLength: 1.75,
          shadowAlpha: 0.38,
          shadowColor: 'rgba(32, 14, 46, 0.38)',
          sunRimColor: '#ff9a5c',
          secondaryRimColor: '#c084fc',
          godRayColor: 'rgba(255, 146, 84, 0.14)',
          godRayAngle: -0.46,
          godRayAlpha: 0.80,
          lanternIntensity: 0.82,
          windowSpillIntensity: 0.85,
          bioIntensity: clamp(sporeLuminescenceDensity * 1.05, 0.62, 0.95),
          cloudShadowAlpha: 0.05,
          vignetteColor: 'rgba(20, 10, 34, 0.44)',
          vignetteAlpha: 0.44,
          bloomIntensity: 0.75
        };
      } else {
        profile = {
          phaseLabel: 'The Feast (20:00–05:30)',
          skyTop: 'rgba(6, 11, 28, 0.48)',
          skyMid: 'rgba(14, 24, 52, 0.38)',
          skyHorizon: 'rgba(22, 46, 68, 0.30)',
          ambientTint: 'rgba(14, 26, 54, 0.34)',
          groundMistColor: 'rgba(50, 245, 200, 0.10)',
          shadowAngle: 0.45,
          shadowDx: 0.62,
          shadowDy: 0.55,
          shadowLength: 1.05,
          shadowAlpha: 0.42,
          shadowColor: 'rgba(4, 8, 20, 0.44)',
          sunRimColor: '#5eead4',
          secondaryRimColor: '#818cf8',
          godRayColor: 'rgba(94, 234, 212, 0.08)',
          godRayAngle: -0.25,
          godRayAlpha: 0.55,
          lanternIntensity: 1.0,
          windowSpillIntensity: 1.0,
          bioIntensity: clamp(sporeLuminescenceDensity * 1.25, 0.78, 1.0),
          cloudShadowAlpha: 0.0,
          vignetteColor: 'rgba(3, 7, 18, 0.56)',
          vignetteAlpha: 0.56,
          bloomIntensity: 0.95
        };
      }

      // Geomagnetic Aurora & Polarity Inversion (kpExo >= 5.0 / >= 7.0)
      const auroraActive = kp >= 5.0;
      const polarityInversion = kp >= 7.0;
      const auroraIntensity = auroraActive
        ? clamp((kp - 4.5) / 3.5, 0.18, 1.0)
        : 0.0;

      const auroraPalette = polarityInversion
        ? Object.freeze({
            primary: '#e879f9',   // Electric violet-magenta
            secondary: '#c026d3', // Deep magenta flare
            tertiary: '#38bdf8',  // Ion cyan-blue
            ribbonGlow: 'rgba(232, 121, 249, 0.28)'
          })
        : Object.freeze({
            primary: '#32f5c8',   // 4900K cyan-emerald mycelial aurora
            secondary: '#38bdf8', // Magnetospheric teal-blue
            tertiary: '#a855f7',  // Upper-altitude violet fringe
            ribbonGlow: 'rgba(50, 245, 200, 0.22)'
          });

      let vignetteAlpha = profile.vignetteAlpha;
      let shadowAlpha = profile.shadowAlpha;
      if (comfort.isHighContrast) {
        vignetteAlpha *= 0.35;
        shadowAlpha = Math.min(0.6, shadowAlpha * 1.2);
      } else if (comfort.isLightTheme) {
        vignetteAlpha *= 0.45;
        shadowAlpha *= 0.8;
      } else if (comfort.isCalmTheme) {
        vignetteAlpha *= 0.75;
      }

      const blueAzimuth = Number(((45 + (tickId - 1) * 90) % 360).toFixed(2));
      const redAzimuth = Number(((210 - (tickId - 1) * 33.75 + 3600) % 360).toFixed(2));

      return {
        dayPhase: resolvedPhase,
        phaseLabel: profile.phaseLabel,
        timeOfDay: hour,
        kpExo: kp,
        kp_exo: kp,
        biomeId: bId,
        active_biome_cell: bTint.cellName,
        micro_climate_regime: microClimateRegime,
        luna_alpha_phase: lunaAlphaPhase,
        luna_beta_phase: lunaBetaPhase,
        luna_gamma_phase: lunaGammaPhase,
        ferrofluid_sea_surge_index: ferrofluidSeaSurgeIndex,
        spore_luminescence_density: sporeLuminescenceDensity,
        geode_charge_capacity_pct: geodeChargeCapacityPct,
        theme: comfort.theme,
        ldsTokens: comfort.ldsTokens,
        reducedMotion: comfort.reducedMotion,
        twinSuns: {
          primaryBlueDwarf: {
            name: 'Sol Alpha (Blue Dwarf)',
            azimuthDeg: blueAzimuth,
            kelvin: 6500,
            color: '#d8f8ff',
            coreColor: '#ffffff',
            visible: resolvedPhase !== 'THE_FEAST'
          },
          secondaryRedGiant: {
            name: 'Sol Beta (Red Giant)',
            azimuthDeg: redAzimuth,
            kelvin: 3100,
            color: '#ff9466',
            coreColor: '#ffd8a8',
            visible: resolvedPhase !== 'THE_FEAST'
          }
        },
        tripleMoons: {
          lunaAlpha: { name: 'Luna Alpha', color: '#5eead4', phase: lunaAlphaPhase },
          lunaBeta: { name: 'Luna Beta', color: '#818cf8', phase: lunaBetaPhase },
          lunaGamma: { name: 'Luna Gamma', color: '#f472b6', phase: lunaGammaPhase },
          ferrofluidSeaSurgeIndex,
          visible: resolvedPhase === 'THE_FEAST' || resolvedPhase === 'DUSK_CRAFT'
        },
        skyGradient: {
          top: profile.skyTop,
          mid: profile.skyMid,
          horizon: profile.skyHorizon
        },
        ambientTint: profile.ambientTint,
        groundMistColor: profile.groundMistColor,
        shadowAngle: profile.shadowAngle,
        shadowDx: profile.shadowDx,
        shadowDy: profile.shadowDy,
        shadowLength: profile.shadowLength,
        shadowAlpha,
        shadowColor: profile.shadowColor,
        sunRimColor: profile.sunRimColor,
        secondaryRimColor: profile.secondaryRimColor,
        godRayColor: profile.godRayColor,
        godRayAngle: profile.godRayAngle,
        godRayAlpha: comfort.isHighContrast ? 0 : profile.godRayAlpha,
        lanternColor: 'rgba(255, 184, 77, 0.45)',
        lanternCoreColor: '#ffdf80',
        lanternKelvin: 2700,
        lanternIntensity: profile.lanternIntensity,
        windowSpillIntensity: profile.windowSpillIntensity,
        bioColor: bTint.sporeColor,
        bioSecondaryColor: bTint.waterHighlight,
        bioKelvin: 4900,
        bioIntensity: profile.bioIntensity,
        cloudShadowAlpha: comfort.isHighContrast ? 0 : profile.cloudShadowAlpha,
        auroraActive,
        auroraIntensity,
        polarityInversion,
        auroraPalette,
        vignetteColor: profile.vignetteColor,
        vignetteAlpha,
        bloomIntensity: comfort.isHighContrast ? 0.2 : profile.bloomIntensity
      };
    }

    // =========================================================================
    // 2. TACTILE 2.5D TERRAIN, BUILDING & WATER MICRO-ARTISTRY
    // =========================================================================

    /**
     * Renders Ferrofluid River & Tide Basin Caustics driven by `ferrofluid_sea_surge_index`:
     * - Shoreline metallic meniscus & foam along land-water boundaries
     * - Multi-layered animated Rosensweig magnetic ripple rings
     * - Specular Twin-Sun & Triple-Moon water glints
     * - Swimming ferro-fish silhouettes beneath the surface
     */
    function renderFerrofluidCaustics(ctx, world, camera, animTick = 0, options = {}) {
      if (!ctx) return;
      const env = normalizeWorldContext(ctx, world, camera, animTick, options);
      const { grid, gridW, gridH, scale, offsetX, offsetY, canvasW, canvasH, timeSec, atmos, biomeTint, kpExo } = env;
      if (!gridH || !gridW) return;

      const surgeIndex = atmos.ferrofluid_sea_surge_index ?? 0.5;
      ctx.save();
      const waterTiles = [];

      for (let y = 0; y < gridH; y++) {
        for (let x = 0; x < gridW; x++) {
          const cellType = getCellType(grid, x, y);
          if (!isWaterCell(cellType)) continue;

          const sx = offsetX + x * scale;
          const sy = offsetY + y * scale;
          if (sx + scale < -scale || sy + scale < -scale || sx > canvasW + scale || sy > canvasH + scale) {
            continue;
          }
          waterTiles.push({ x, y, sx, sy });

          // 1. Shoreline Metallic Meniscus & Colloidal Foam (modulated by ferrofluid_sea_surge_index)
          const topLand = !isWaterCell(getCellType(grid, x, y - 1));
          const bottomLand = !isWaterCell(getCellType(grid, x, y + 1));
          const leftLand = !isWaterCell(getCellType(grid, x - 1, y));
          const rightLand = !isWaterCell(getCellType(grid, x + 1, y));

          const foamWave = Math.sin(timeSec * 2.2 + x * 0.7 + y * 0.5) * (1.0 + surgeIndex * 1.2);
          const foamThickness = Math.max(2, scale * (0.09 + surgeIndex * 0.06));
          ctx.fillStyle = `rgba(180, 248, 255, ${(0.22 + surgeIndex * 0.14).toFixed(3)})`;
          if (topLand) {
            ctx.fillRect(sx, sy + Math.max(0, foamWave), scale + 0.5, foamThickness);
          }
          if (bottomLand) {
            ctx.fillRect(sx, sy + scale - foamThickness + foamWave * 0.4, scale + 0.5, foamThickness);
          }
          if (leftLand) {
            ctx.fillRect(sx, sy, foamThickness, scale + 0.5);
          }
          if (rightLand) {
            ctx.fillRect(sx + scale - foamThickness, sy, foamThickness, scale + 0.5);
          }

          // 2. Rosensweig Ferrofluid Magnetic Standing-Wave Rings
          const seed = hash2D(x, y, 11);
          if (seed > 0.38) {
            const cx = sx + scale * (0.35 + seed * 0.3);
            const cy = sy + scale * (0.35 + hash2D(x, y, 23) * 0.3);
            const phase = (timeSec * (0.8 + kpExo * 0.08 + surgeIndex * 0.4) + seed * 6.28) % (Math.PI * 2);
            const normWave = (Math.sin(phase) + 1) * 0.5;
            const maxR = scale * (0.22 + surgeIndex * 0.14 + (kpExo >= 5.0 ? 0.1 : 0));
            const r1 = maxR * (0.35 + normWave * 0.65);

            ctx.strokeStyle = atmos.polarityInversion
              ? `rgba(232, 121, 249, ${(0.40 * (1 - normWave * 0.55)).toFixed(3)})`
              : `rgba(94, 234, 212, ${(0.36 * (1 - normWave * 0.55)).toFixed(3)})`;
            ctx.lineWidth = Math.max(1, scale * 0.045);
            ctx.beginPath();
            ctx.arc(cx, cy, r1, 0, Math.PI * 2);
            ctx.stroke();

            if (kpExo >= 4.2 && seed > 0.62) {
              ctx.fillStyle = atmos.polarityInversion ? '#f0abfc' : biomeTint.waterHighlight;
              ctx.beginPath();
              ctx.arc(cx, cy, Math.max(1.3, scale * 0.065), 0, Math.PI * 2);
              ctx.fill();
            }
          }

          // 3. Twin-Sun & Triple-Moon Specular Diamond Water Glints
          const glintSeed = hash2D(x, y, 37);
          const glintPulse = Math.sin(timeSec * 3.4 + glintSeed * 18.0);
          if (glintPulse > 0.6) {
            const gx = sx + scale * (0.2 + glintSeed * 0.6);
            const gy = sy + scale * (0.2 + hash2D(x, y, 53) * 0.6);
            const gSize = Math.max(1.8, scale * 0.11 * ((glintPulse - 0.6) / 0.4));

            ctx.fillStyle = glintSeed > 0.5 ? atmos.sunRimColor : atmos.secondaryRimColor;
            ctx.beginPath();
            ctx.moveTo(gx, gy - gSize);
            ctx.lineTo(gx + gSize * 1.2, gy);
            ctx.lineTo(gx, gy + gSize);
            ctx.lineTo(gx - gSize * 1.2, gy);
            ctx.closePath();
            ctx.fill();
          }
        }
      }

      // 4. Swimming Ferro-Fish Silhouettes Beneath the Surface
      if (waterTiles.length > 4) {
        const fishCount = Math.min(6, Math.max(2, Math.floor(waterTiles.length / 22)));
        for (let i = 0; i < fishCount; i++) {
          const anchorTile = waterTiles[(i * 19 + 7) % waterTiles.length];
          const swimPhase = timeSec * (0.9 + (i % 3) * 0.25) + i * 2.1;
          const fx = anchorTile.sx + scale * 0.5 + Math.cos(swimPhase) * scale * 0.85;
          const fy = anchorTile.sy + scale * 0.5 + Math.sin(swimPhase * 1.4) * scale * 0.32;
          const dirAngle = Math.atan2(
            Math.cos(swimPhase * 1.4) * 1.4 * 0.32,
            -Math.sin(swimPhase) * 0.85
          );

          ctx.save();
          ctx.translate(fx, fy);
          ctx.rotate(dirAngle);

          const bodyLen = Math.max(5, scale * 0.28);
          const bodyWid = Math.max(2.2, scale * 0.11);
          ctx.fillStyle = 'rgba(6, 22, 32, 0.52)';
          ctx.beginPath();
          ctx.ellipse(0, 0, bodyLen, bodyWid, 0, 0, Math.PI * 2);
          ctx.fill();

          const tailWag = Math.sin(timeSec * 8 + i) * (bodyWid * 0.45);
          ctx.beginPath();
          ctx.moveTo(-bodyLen * 0.85, 0);
          ctx.lineTo(-bodyLen * 1.45, -bodyWid * 0.9 + tailWag);
          ctx.lineTo(-bodyLen * 1.45, bodyWid * 0.9 + tailWag);
          ctx.closePath();
          ctx.fill();

          ctx.fillStyle = 'rgba(94, 234, 212, 0.42)';
          ctx.beginPath();
          ctx.ellipse(bodyLen * 0.15, 0, bodyLen * 0.45, bodyWid * 0.35, 0, 0, Math.PI * 2);
          ctx.fill();

          ctx.restore();
        }
      }

      ctx.restore();
    }

    /**
     * Renders Tactile 2.5D Terrain & Living Flora Micro-Details:
     * - Gently swaying Crystalline Iron-Wheat stalks
     * - Pulsing bioluminescent spore-mushrooms scaled by `spore_luminescence_density`
     * - Cobblestone & Main Bus copper conduit seams
     * - Stepped tree canopy rim-highlights & directional drop shadows
     * - Sparkling geode fissure glints (`✦`) scaled by `geode_charge_capacity_pct`
     */
    function renderTerrainMicroDetails(ctx, world, camera, animTick = 0, options = {}) {
      if (!ctx) return;
      const env = normalizeWorldContext(ctx, world, camera, animTick, options);
      const {
        grid,
        gridW,
        gridH,
        scale,
        offsetX,
        offsetY,
        canvasW,
        canvasH,
        timeSec,
        atmos,
        biomeTint,
        trees,
        resourceNodes,
        geodeObelisk
      } = env;

      const sporeDensity = atmos.spore_luminescence_density ?? 0.5;
      const geodeChargeNorm = (atmos.geode_charge_capacity_pct ?? 60) / 100;

      ctx.save();

      // 1. Tile Micro-Flora, Iron-Wheat Stalks, Spore-Mushrooms & Cobblestone Seams
      if (gridH > 0 && gridW > 0) {
        for (let y = 0; y < gridH; y++) {
          for (let x = 0; x < gridW; x++) {
            const sx = offsetX + x * scale;
            const sy = offsetY + y * scale;
            if (sx + scale < 0 || sy + scale < 0 || sx > canvasW || sy > canvasH) continue;

            const cellType = getCellType(grid, x, y);
            const h1 = hash2D(x, y, 1);
            const h2 = hash2D(x, y, 2);

            if (cellType === 'crop') {
              const sway = Math.sin(timeSec * 2.1 + x * 0.8 + y * 0.5) * (scale * 0.08);
              for (let s = 0; s < 3; s++) {
                const bx = sx + scale * (0.24 + s * 0.25);
                const by = sy + scale * 0.82;
                const tipX = bx + sway;
                const tipY = sy + scale * 0.22;

                ctx.strokeStyle = '#d4af37';
                ctx.lineWidth = Math.max(1.2, scale * 0.055);
                ctx.beginPath();
                ctx.moveTo(bx, by);
                ctx.quadraticCurveTo(bx + sway * 0.4, (by + tipY) * 0.5, tipX, tipY);
                ctx.stroke();

                ctx.fillStyle = s === 1 ? '#5eead4' : '#fde047';
                ctx.beginPath();
                ctx.arc(tipX, tipY, Math.max(1.4, scale * 0.065), 0, Math.PI * 2);
                ctx.fill();
              }
            } else if (cellType === 'road' || cellType === 'plaza') {
              if (h1 > 0.55) {
                ctx.fillStyle = 'rgba(240, 188, 104, 0.16)';
                ctx.fillRect(
                  sx + scale * (0.18 + h2 * 0.45),
                  sy + scale * (0.22 + h1 * 0.45),
                  Math.max(2, scale * 0.22),
                  Math.max(1.5, scale * 0.12)
                );
              }
              if (cellType === 'plaza' && (x + y) % 2 === 0) {
                ctx.strokeStyle = 'rgba(50, 245, 200, 0.18)';
                ctx.lineWidth = 1;
                ctx.strokeRect(sx + 2, sy + 2, scale - 4, scale - 4);
              }
            } else if (cellType === 'grass' || !cellType) {
              // Spore-mushroom spawn threshold scales with `spore_luminescence_density`
              const mushroomThreshold = 0.90 - sporeDensity * 0.08;
              if (h1 > mushroomThreshold) {
                const mx = sx + scale * (0.25 + h2 * 0.5);
                const my = sy + scale * (0.35 + (1 - h2) * 0.45);
                const pulse = 0.65 + 0.35 * Math.sin(timeSec * 2.6 + h1 * 12.0);
                const capR = Math.max(2, scale * 0.1);

                if (atmos.bioIntensity > 0.22) {
                  const glowGrad = ctx.createRadialGradient(mx, my, 0, mx, my, capR * 3.4);
                  glowGrad.addColorStop(
                    0,
                    `rgba(50, 245, 200, ${(0.32 * atmos.bioIntensity * pulse).toFixed(3)})`
                  );
                  glowGrad.addColorStop(1, 'rgba(50, 245, 200, 0)');
                  ctx.fillStyle = glowGrad;
                  ctx.beginPath();
                  ctx.arc(mx, my, capR * 3.4, 0, Math.PI * 2);
                  ctx.fill();
                }

                ctx.fillStyle = '#e2e8f0';
                ctx.fillRect(mx - capR * 0.3, my, capR * 0.6, capR * 0.9);
                ctx.fillStyle = h2 > 0.5 ? biomeTint.sporeColor : '#34d399';
                ctx.beginPath();
                ctx.arc(mx, my, capR, Math.PI, 0);
                ctx.fill();
              } else if (h1 < 0.14) {
                const gx = sx + scale * (0.3 + h2 * 0.4);
                const gy = sy + scale * (0.4 + h1 * 2.0);
                const sway = Math.sin(timeSec * 1.8 + x + y) * (scale * 0.05);
                ctx.strokeStyle = 'rgba(110, 231, 183, 0.28)';
                ctx.lineWidth = Math.max(1, scale * 0.04);
                ctx.beginPath();
                ctx.moveTo(gx, gy);
                ctx.lineTo(gx - scale * 0.06 + sway, gy - scale * 0.16);
                ctx.moveTo(gx, gy);
                ctx.lineTo(gx + scale * 0.06 + sway, gy - scale * 0.18);
                ctx.stroke();
              }
            }
          }
        }
      }

      // 2. Central Plaza Captured-Lightning Geode Obelisk Resonance Rings
      if (geodeObelisk && Number.isFinite(geodeObelisk.x)) {
        const ox = offsetX + (geodeObelisk.x + 0.5) * scale;
        const oy = offsetY + (geodeObelisk.y + 0.5) * scale;
        const pulse = 0.7 + 0.3 * Math.sin(timeSec * 2.4);
        const obRadius = scale * (2.1 + geodeChargeNorm * 0.75);
        const obGrad = ctx.createRadialGradient(ox, oy, scale * 0.1, ox, oy, obRadius);
        obGrad.addColorStop(0, `rgba(50, 245, 200, ${(0.36 * pulse).toFixed(3)})`);
        obGrad.addColorStop(0.5, `rgba(240, 188, 104, ${(0.18 * pulse).toFixed(3)})`);
        obGrad.addColorStop(1, 'rgba(50, 245, 200, 0)');
        ctx.fillStyle = obGrad;
        ctx.beginPath();
        ctx.arc(ox, oy, obRadius, 0, Math.PI * 2);
        ctx.fill();
      }

      // 3. Stepped Tree Canopy Sunlight/Moonlight Rim-Highlights & Directional Shadows
      if (Array.isArray(trees)) {
        for (let i = 0; i < trees.length; i++) {
          const t = trees[i];
          const tx = offsetX + t.x * scale;
          const ty = offsetY + t.y * scale;
          if (tx + scale * 2 < 0 || ty + scale * 2 < 0 || tx - scale > canvasW || ty - scale > canvasH) {
            continue;
          }

          ctx.fillStyle = atmos.shadowColor;
          ctx.beginPath();
          ctx.ellipse(
            tx + scale * (0.5 + atmos.shadowDx * 0.38),
            ty + scale * (0.75 + atmos.shadowDy * 0.25),
            scale * 0.58 * atmos.shadowLength,
            scale * 0.32,
            0,
            0,
            Math.PI * 2
          );
          ctx.fill();

          ctx.strokeStyle = atmos.sunRimColor;
          ctx.lineWidth = Math.max(1.5, scale * 0.065);
          ctx.globalAlpha = 0.55;
          ctx.beginPath();
          const topCanopyY = ty - scale * 1.1;
          ctx.moveTo(tx + scale * 0.15, topCanopyY + scale * 0.25);
          ctx.lineTo(tx + scale * 0.15, topCanopyY);
          ctx.lineTo(tx + scale * 0.85, topCanopyY);
          ctx.stroke();
          ctx.globalAlpha = 1.0;
        }
      }

      // 4. Sparkling Geode Fissure Glints (✦) & Interactive Node Halos
      if (Array.isArray(resourceNodes)) {
        for (let i = 0; i < resourceNodes.length; i++) {
          const n = resourceNodes[i];
          const nx = offsetX + (n.x + 0.5) * scale;
          const ny = offsetY + (n.y + 0.5) * scale;
          if (nx + scale < 0 || ny + scale < 0 || nx - scale > canvasW || ny - scale > canvasH) continue;

          const sparklePhase = timeSec * 3.2 + i * 1.3;
          const sparkleScale = 0.65 + 0.35 * Math.sin(sparklePhase);
          const haloR = scale * (0.45 + 0.18 * geodeChargeNorm * sparkleScale);

          const haloGrad = ctx.createRadialGradient(nx, ny, 0, nx, ny, haloR);
          const isGeode = n.type === 'geode' || String(n.id || '').includes('geode');
          haloGrad.addColorStop(
            0,
            isGeode ? 'rgba(255, 216, 102, 0.42)' : 'rgba(50, 245, 200, 0.32)'
          );
          haloGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
          ctx.fillStyle = haloGrad;
          ctx.beginPath();
          ctx.arc(nx, ny, haloR, 0, Math.PI * 2);
          ctx.fill();

          if (isGeode || sparkleScale > 0.76) {
            const starR = Math.max(3, scale * (0.18 + 0.08 * geodeChargeNorm) * sparkleScale);
            const sxStar = nx + Math.cos(i * 2.4) * scale * 0.22;
            const syStar = ny - scale * 0.22;
            ctx.fillStyle = isGeode ? '#fffbeb' : '#a7f3d0';
            ctx.beginPath();
            ctx.moveTo(sxStar, syStar - starR);
            ctx.lineTo(sxStar + starR * 0.28, syStar - starR * 0.28);
            ctx.lineTo(sxStar + starR, syStar);
            ctx.lineTo(sxStar + starR * 0.28, syStar + starR * 0.28);
            ctx.lineTo(sxStar, syStar + starR);
            ctx.lineTo(sxStar - starR * 0.28, syStar + starR * 0.28);
            ctx.lineTo(sxStar - starR, syStar);
            ctx.lineTo(sxStar - starR * 0.28, syStar - starR * 0.28);
            ctx.closePath();
            ctx.fill();
          }
        }
      }

      ctx.restore();
    }

    /**
     * Renders 2.5D Architectural Depth, Warmth & `crucible-automata` 4 Aegis Hearth Elemental Motifs:
     * - Soft ambient-occlusion (AO) contact shadows at building bases
     * - Directional roof-overhang drop shadows
     * - Warm 2700K multi-paned window light pools cast onto cobblestone roads at dusk/night
     * - Hanging copper street-lanterns with gentle pendulum sway
     * - `crucible-automata` 4 Elemental Sanctuary Motifs (`PorchHearth` embers->starlight dew,
     *   `RainGarden` cascading spring droplets, `FlowHourglass` conserved golden sand stream,
     *   `AlchemistCrucible` molten smelting + aether crystal glow)
     */
    function renderBuildingArtisticPass(ctx, world, camera, animTick = 0, options = {}) {
      if (!ctx) return;
      const env = normalizeWorldContext(ctx, world, camera, animTick, options);
      const {
        buildings,
        decorations,
        scale,
        offsetX,
        offsetY,
        canvasW,
        canvasH,
        timeSec,
        atmos
      } = env;

      ctx.save();

      for (let i = 0; i < buildings.length; i++) {
        const b = buildings[i];
        const bx = offsetX + b.x * scale;
        const by = offsetY + b.y * scale;
        const bw = b.w * scale;
        const bd = b.d * scale;
        const bh = Math.max(scale * 0.6, b.h * scale * 0.45);

        if (bx + bw + scale * 2 < 0 || by + bd + scale * 2 < 0 || bx - scale * 2 > canvasW || by - bh - scale * 2 > canvasH) {
          continue;
        }

        // 1. Directional Roof-Overhang & Building Drop Shadow
        const shX = atmos.shadowDx * scale * 0.55 * atmos.shadowLength;
        const shY = atmos.shadowDy * scale * 0.45 * atmos.shadowLength;
        ctx.fillStyle = atmos.shadowColor;
        ctx.beginPath();
        ctx.moveTo(bx, by + bd);
        ctx.lineTo(bx + bw, by + bd);
        ctx.lineTo(bx + bw + shX, by + bd + shY);
        ctx.lineTo(bx + shX, by + bd + shY);
        ctx.closePath();
        ctx.fill();

        // 2. Soft Ambient-Occlusion (AO) Contact Shadow at Building Base
        const aoGrad = ctx.createLinearGradient(bx, by + bd - scale * 0.15, bx, by + bd + scale * 0.35);
        aoGrad.addColorStop(0, 'rgba(0, 0, 0, 0.42)');
        aoGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = aoGrad;
        ctx.fillRect(bx - 2, by + bd - scale * 0.1, bw + 4, scale * 0.42);

        // 3. Sunlit/Moonlit Roof Rim Highlight
        ctx.strokeStyle = atmos.sunRimColor;
        ctx.lineWidth = Math.max(1.5, scale * 0.06);
        ctx.globalAlpha = 0.52;
        ctx.beginPath();
        ctx.moveTo(bx, by - bh + bd * 0.35);
        ctx.lineTo(bx, by - bh);
        ctx.lineTo(bx + bw, by - bh);
        ctx.stroke();
        ctx.globalAlpha = 1.0;

        // 4. Warm 2700K Multi-Paned Window Light Pools Cast onto Roads at Dusk/Night
        if (atmos.windowSpillIntensity > 0.12) {
          const spillAlpha = 0.32 * atmos.windowSpillIntensity;
          const winPositions = [0.24, 0.76];
          ctx.save();
          ctx.globalCompositeOperation = 'screen';

          for (const wp of winPositions) {
            const wx = bx + bw * wp;
            const wy = by + bd;
            const spillLen = scale * (0.95 + atmos.windowSpillIntensity * 0.45);
            const spillGrad = ctx.createRadialGradient(wx, wy, scale * 0.05, wx, wy + spillLen * 0.5, spillLen);
            spillGrad.addColorStop(0, `rgba(255, 214, 112, ${(spillAlpha * 1.15).toFixed(3)})`);
            spillGrad.addColorStop(0.55, `rgba(255, 168, 68, ${(spillAlpha * 0.65).toFixed(3)})`);
            spillGrad.addColorStop(1, 'rgba(255, 140, 40, 0)');

            ctx.fillStyle = spillGrad;
            ctx.beginPath();
            ctx.moveTo(wx - scale * 0.25, wy - scale * 0.05);
            ctx.lineTo(wx + scale * 0.25, wy - scale * 0.05);
            ctx.lineTo(wx + scale * 0.65 + shX * 0.25, wy + spillLen);
            ctx.lineTo(wx - scale * 0.65 + shX * 0.25, wy + spillLen);
            ctx.closePath();
            ctx.fill();
          }
          ctx.restore();
        }

        // 5. Hanging Copper Street-Lanterns with Gentle Pendulum Sway
        const swayAngle = Math.sin(timeSec * 2.0 + i * 1.1) * 0.14;
        const lanternAnchorX = bx + bw * 0.5;
        const lanternAnchorY = by + bd - bh * 0.55;
        const cordLen = Math.max(4, scale * 0.22);
        const lx = lanternAnchorX + Math.sin(swayAngle) * cordLen;
        const ly = lanternAnchorY + Math.cos(swayAngle) * cordLen;

        ctx.strokeStyle = '#d97706';
        ctx.lineWidth = Math.max(1, scale * 0.045);
        ctx.beginPath();
        ctx.moveTo(lanternAnchorX, lanternAnchorY);
        ctx.lineTo(lx, ly);
        ctx.stroke();

        const lRadius = Math.max(2.2, scale * 0.1);
        ctx.fillStyle = atmos.lanternIntensity > 0.35 ? '#fde047' : '#fbbf24';
        ctx.beginPath();
        ctx.arc(lx, ly, lRadius, 0, Math.PI * 2);
        ctx.fill();

        if (atmos.lanternIntensity > 0.15) {
          ctx.save();
          ctx.globalCompositeOperation = 'screen';
          const haloR = scale * (0.7 + atmos.lanternIntensity * 0.65);
          const lGrad = ctx.createRadialGradient(lx, ly, 0, lx, ly, haloR);
          lGrad.addColorStop(0, `rgba(255, 220, 120, ${(0.48 * atmos.lanternIntensity).toFixed(3)})`);
          lGrad.addColorStop(0.5, `rgba(255, 164, 60, ${(0.22 * atmos.lanternIntensity).toFixed(3)})`);
          lGrad.addColorStop(1, 'rgba(255, 140, 40, 0)');
          ctx.fillStyle = lGrad;
          ctx.beginPath();
          ctx.arc(lx, ly, haloR, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }

        // 6. Crucible-Automata 4 Aegis Hearth Elemental Motifs per Landmark
        const motif = b.motif || AEGIS_HEARTH_MOTIFS.AlchemistCrucible;
        const chimX = bx + bw * 0.78;
        const chimY = by - bh - scale * 0.08;

        if (motif.id === 'PorchHearth') {
          // Scene I: Warm embers rise through carved stone and condense into starlight dew above
          for (let p = 0; p < 4; p++) {
            const cycle = (timeSec * 0.52 + p * 0.25 + i * 0.17) % 1.0;
            const px = chimX + Math.sin(cycle * 6.28 + i) * scale * 0.2 + cycle * scale * 0.25;
            const py = chimY - cycle * scale * 1.45;
            const isDewCondensation = cycle > 0.68;
            ctx.fillStyle = isDewCondensation ? motif.dewColor : motif.primaryColor;
            ctx.globalAlpha = (1 - cycle * 0.75) * 0.65;
            ctx.beginPath();
            ctx.arc(px, py, Math.max(1.5, scale * (isDewCondensation ? 0.08 : 0.12)), 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.globalAlpha = 1.0;
        } else if (motif.id === 'RainGarden') {
          // Scene II: Mossling's Rain Garden cascading spring water & crystal flora shimmer
          for (let p = 0; p < 3; p++) {
            const dropCycle = (timeSec * 0.65 + p * 0.33 + i * 0.2) % 1.0;
            const dx = bx + bw * (0.2 + p * 0.3);
            const dy = by + bd - scale * 0.3 + dropCycle * scale * 0.35;
            ctx.strokeStyle = motif.secondaryColor;
            ctx.globalAlpha = 0.45 * (1 - dropCycle);
            ctx.lineWidth = Math.max(1, scale * 0.045);
            ctx.beginPath();
            ctx.arc(dx, dy, scale * 0.15 * dropCycle, 0, Math.PI * 2);
            ctx.stroke();
          }
          ctx.globalAlpha = 1.0;
        } else if (motif.id === 'FlowHourglass') {
          // Scene III: The Hourglass of Flow conserved golden sand trickling through roof aperture
          const hgX = bx + bw * 0.5;
          const hgY = by - bh * 0.55;
          const sandGrainY = hgY + ((timeSec * 0.8 + i * 0.3) % 1.0) * (scale * 0.28);
          ctx.fillStyle = motif.sandColor;
          ctx.globalAlpha = 0.75;
          ctx.beginPath();
          ctx.arc(hgX, sandGrainY, Math.max(1.4, scale * 0.055), 0, Math.PI * 2);
          ctx.fill();
          ctx.globalAlpha = 1.0;
        } else {
          // Scene IV: The Alchemist's Crucible smelting plume & starlight crystal spark
          for (let p = 0; p < 4; p++) {
            const cycle = (timeSec * 0.58 + p * 0.25 + i * 0.13) % 1.0;
            const px = chimX + Math.cos(cycle * 6.28 + p) * scale * 0.18;
            const py = chimY - cycle * scale * 1.35;
            ctx.fillStyle = p % 2 === 0 ? motif.primaryColor : motif.secondaryColor;
            ctx.globalAlpha = (1 - cycle) * 0.55;
            ctx.beginPath();
            ctx.arc(px, py, scale * (0.09 + cycle * 0.14), 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.globalAlpha = 1.0;
        }
      }

      // 7. Placed Yard Lanterns & Decorations Glow
      if (Array.isArray(decorations)) {
        for (let i = 0; i < decorations.length; i++) {
          const d = decorations[i];
          const dx = offsetX + (d.x + 0.5) * scale;
          const dy = offsetY + (d.y + 0.35) * scale;
          if (dx + scale < 0 || dy + scale < 0 || dx - scale > canvasW || dy - scale > canvasH) continue;

          ctx.save();
          ctx.globalCompositeOperation = 'screen';
          const decR = scale * 0.85;
          const dGrad = ctx.createRadialGradient(dx, dy, 0, dx, dy, decR);
          dGrad.addColorStop(0, 'rgba(50, 245, 200, 0.32)');
          dGrad.addColorStop(0.6, 'rgba(240, 188, 104, 0.14)');
          dGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
          ctx.fillStyle = dGrad;
          ctx.beginPath();
          ctx.arc(dx, dy, decR, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
      }

      ctx.restore();
    }

    // =========================================================================
    // 3. EXPRESSIVE CHARACTER & WILLOW COMPANION RENDERING
    // =========================================================================

    /**
     * Renders Willow (`enclave_07_willow`) signature artistic presence:
     * - Soft emerald-gold alchemical ground ring with 4 cardinal runes
     * - Flowing copper hair highlights & glowing alchemist visor scanline
     * - Floating equipped Animal Crossing tool badge
     * - Special Libra Aesthete Feng-Shui Sparkle Aura when Polarity Inversion is active
     */
    function renderWillowArtisticAura(
      ctx,
      willowEntity,
      world,
      camera,
      animTick = 0,
      options = {}
    ) {
      if (!ctx) return;
      const env = normalizeWorldContext(ctx, world, camera, animTick, options);
      const { scale, offsetX, offsetY, timeSec, atmos, citizens, equippedToolId } = env;

      const willow =
        willowEntity && Number.isFinite(Number(willowEntity.x))
          ? willowEntity
          : citizens.find(c => c.id === 'enclave_07_willow') ||
            (world?.willow ? { id: 'enclave_07_willow', x: world.willow.x, y: world.willow.y } : null);

      if (!willow) return;

      const wx = offsetX + willow.x * scale;
      const wy = offsetY + willow.y * scale;
      const bob = env.comfort.reducedMotion
        ? 0
        : Math.abs(Math.sin(willow.walkPhase || timeSec * 4)) * (scale * 0.1);

      ctx.save();

      // 1. Soft Emerald-Gold Alchemical Ground Ring
      const ringRadius = scale * 0.68;
      const rot = timeSec * 0.85;

      const groundGlow = ctx.createRadialGradient(
        wx,
        wy + scale * 0.08,
        scale * 0.08,
        wx,
        wy + scale * 0.08,
        ringRadius * 1.45
      );
      groundGlow.addColorStop(0, 'rgba(50, 245, 200, 0.34)');
      groundGlow.addColorStop(0.55, 'rgba(240, 188, 104, 0.18)');
      groundGlow.addColorStop(1, 'rgba(50, 245, 200, 0)');
      ctx.fillStyle = groundGlow;
      ctx.beginPath();
      ctx.ellipse(wx, wy + scale * 0.08, ringRadius * 1.35, ringRadius * 0.82, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = atmos.ldsTokens.accentPrimary || '#32f5c8';
      ctx.lineWidth = Math.max(1.3, scale * 0.055);
      ctx.beginPath();
      ctx.ellipse(wx, wy + scale * 0.08, ringRadius, ringRadius * 0.58, 0, 0, Math.PI * 2);
      ctx.stroke();

      for (let k = 0; k < 4; k++) {
        const angle = rot + (k * Math.PI) / 2;
        const nx = wx + Math.cos(angle) * ringRadius;
        const ny = wy + scale * 0.08 + Math.sin(angle) * (ringRadius * 0.58);
        ctx.fillStyle = k % 2 === 0 ? '#fde047' : '#32f5c8';
        ctx.beginPath();
        ctx.arc(nx, ny, Math.max(1.8, scale * 0.075), 0, Math.PI * 2);
        ctx.fill();
      }

      // 2. Flowing Copper Hair Highlights & Glowing Visor Scanline
      const headTopY = wy - scale * 0.82 - bob;
      ctx.fillStyle = '#fbbf24';
      ctx.fillRect(wx - scale * 0.24, headTopY, scale * 0.48, Math.max(2, scale * 0.1));

      const visorY = wy - scale * 0.62 - bob;
      ctx.fillStyle = '#32f5c8';
      ctx.fillRect(wx - scale * 0.18, visorY, scale * 0.36, Math.max(2, scale * 0.08));

      // 3. Floating Equipped Animal Crossing Tool Badge
      const toolIcon = options?.toolIcon || TOOL_ICONS[equippedToolId] || '⚗️';
      const badgeX = wx + scale * 0.64;
      const badgeY = wy - scale * 0.58 - bob + Math.sin(timeSec * 3.0) * (scale * 0.06);
      const badgeR = Math.max(7, scale * 0.28);

      ctx.fillStyle = atmos.ldsTokens.bgSurface || 'rgba(13, 29, 24, 0.92)';
      ctx.beginPath();
      ctx.arc(badgeX, badgeY, badgeR, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#f0bc68';
      ctx.lineWidth = Math.max(1.2, scale * 0.05);
      ctx.stroke();

      ctx.font = `${Math.max(10, Math.round(scale * 0.38))}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(toolIcon, badgeX, badgeY + 0.5);

      // 4. Special Libra Aesthete Feng-Shui Sparkle Aura (Polarity Inversion or high Kp_exo)
      if (atmos.polarityInversion || env.kpExo >= 6.0 || options?.forceLibraAura) {
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        const libraRadius = scale * 1.05;
        ctx.strokeStyle = 'rgba(232, 121, 249, 0.68)';
        ctx.lineWidth = Math.max(1.4, scale * 0.055);
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.arc(wx, wy - scale * 0.3 - bob, libraRadius, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        for (let s = 0; s < 6; s++) {
          const sa = -rot * 1.4 + (s * Math.PI * 2) / 6;
          const sx = wx + Math.cos(sa) * libraRadius;
          const sy = wy - scale * 0.3 - bob + Math.sin(sa) * (libraRadius * 0.72);
          ctx.fillStyle = s % 2 === 0 ? '#fde047' : '#e879f9';
          ctx.beginPath();
          ctx.arc(sx, sy, Math.max(2, scale * 0.085), 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }

      ctx.restore();
    }

    function roundRectPath(ctx, x, y, w, h, r) {
      const radius = Math.min(r, w / 2, h / 2);
      ctx.beginPath();
      ctx.moveTo(x + radius, y);
      ctx.lineTo(x + w - radius, y);
      ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
      ctx.lineTo(x + w, y + h - radius);
      ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
      ctx.lineTo(x + radius, y + h);
      ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
      ctx.lineTo(x, y + radius);
      ctx.quadraticCurveTo(x, y, x + radius, y);
      ctx.closePath();
    }

    /**
     * Renders Expressive Character Details for all 16 Enclave Citizens:
     * - Soft directional ground shadows
     * - Subtle breathing/walk squash-and-stretch rim highlights (squad-colored)
     * - Cooperative bond resonance filaments between nearby neighbors
     * - Cozy Animal Crossing-style rounded speech/thought bubbles with tail pointers
     */
    function renderCitizenArtisticPass(
      ctx,
      citizensInput,
      world,
      camera,
      animTick = 0,
      options = {}
    ) {
      let actualWorld = world;
      let actualCamera = camera;
      let actualTick = animTick;
      let actualOptions = options;
      if (
        citizensInput &&
        !Array.isArray(citizensInput) &&
        typeof citizensInput === 'object' &&
        (citizensInput.grid || citizensInput.citizens || citizensInput.biomeId || citizensInput.dayPhase)
      ) {
        actualOptions = animTick && typeof animTick === 'object' ? animTick : {};
        actualTick = typeof camera === 'number' ? camera : 0;
        actualCamera = world;
        actualWorld = citizensInput;
      }

      if (!ctx) return;
      const env = normalizeWorldContext(ctx, actualWorld, actualCamera, actualTick, actualOptions);
      const list =
        Array.isArray(citizensInput) && citizensInput.length > 0
          ? citizensInput.map((c, idx) => ({
              id: c.id || c.characterId || `c_${idx}`,
              name: c.name || 'Citizen',
              squad: c.squad || 'The Wilds',
              x: Number(c.x ?? 22),
              y: Number(c.y ?? 22),
              walkPhase: Number(c.walkPhase ?? idx * 0.7),
              bubbleText: c.bubbleTimer > 0 ? c.bubbleText : c.bubbleText || ''
            }))
          : env.citizens;

      const { scale, offsetX, offsetY, canvasW, canvasH, timeSec, atmos } = env;
      if (!list || list.length === 0) return;

      ctx.save();

      // 1. Cooperative Camaraderie Bond Filaments between nearby citizens
      const willow = list.find(c => c.id === 'enclave_07_willow');
      if (willow) {
        const wx = offsetX + willow.x * scale;
        const wy = offsetY + willow.y * scale;
        for (let i = 0; i < list.length; i++) {
          const c = list[i];
          if (c.id === 'enclave_07_willow') continue;
          const dist = Math.hypot(c.x - willow.x, c.y - willow.y);
          if (dist < 3.2) {
            const cx = offsetX + c.x * scale;
            const cy = offsetY + c.y * scale;
            const alpha = clamp((3.2 - dist) / 3.2, 0.1, 0.45);
            ctx.strokeStyle = `rgba(50, 245, 200, ${alpha.toFixed(3)})`;
            ctx.lineWidth = Math.max(1.2, scale * 0.05);
            ctx.beginPath();
            ctx.moveTo(wx, wy - scale * 0.25);
            ctx.quadraticCurveTo(
              (wx + cx) * 0.5,
              Math.min(wy, cy) - scale * 0.65,
              cx,
              cy - scale * 0.25
            );
            ctx.stroke();
          }
        }
      }

      // 2. Per-Citizen Directional Shadows, Rim Highlights & Rounded Speech Bubbles
      for (let i = 0; i < list.length; i++) {
        const c = list[i];
        const cx = offsetX + c.x * scale;
        const cy = offsetY + c.y * scale;
        if (cx + scale * 2 < 0 || cy + scale * 2 < 0 || cx - scale * 2 > canvasW || cy - scale * 2 > canvasH) {
          continue;
        }

        const isWillow = c.id === 'enclave_07_willow';
        const bob = env.comfort.reducedMotion
          ? 0
          : Math.abs(Math.sin((c.walkPhase || 0) + timeSec * 2.2)) * (scale * 0.11);

        const shX = cx + atmos.shadowDx * scale * 0.18;
        const shY = cy + scale * 0.14 + atmos.shadowDy * scale * 0.1;
        ctx.fillStyle = atmos.shadowColor;
        ctx.beginPath();
        ctx.ellipse(
          shX,
          shY,
          scale * 0.34 * Math.min(1.4, atmos.shadowLength),
          scale * 0.16,
          0,
          0,
          Math.PI * 2
        );
        ctx.fill();

        const squadRim = SQUAD_RIM_COLORS[c.squad] || '#32f5c8';
        ctx.strokeStyle = isWillow ? '#fde047' : squadRim;
        ctx.lineWidth = Math.max(1.3, scale * 0.055);
        ctx.globalAlpha = 0.72;
        ctx.beginPath();
        ctx.arc(cx, cy - scale * 0.45 - bob, scale * 0.28, Math.PI * 1.1, Math.PI * 1.9);
        ctx.stroke();
        ctx.globalAlpha = 1.0;

        if (c.bubbleText && env.options.renderSpeechBubbles !== false) {
          const text = String(c.bubbleText).slice(0, 64);
          ctx.font = `600 ${Math.max(10, Math.round(scale * 0.36))}px system-ui, sans-serif`;
          const textW = ctx.measureText(text).width;
          const padX = 11;
          const boxW = Math.max(48, textW + padX * 2);
          const boxH = Math.max(20, Math.round(scale * 0.72));
          const boxX = cx - boxW / 2;
          const boxY = cy - scale * 1.82 - bob;

          ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
          roundRectPath(ctx, boxX + 2, boxY + 2, boxW, boxH, 9);
          ctx.fill();

          ctx.fillStyle = atmos.ldsTokens.bgSurface || 'rgba(11, 25, 22, 0.94)';
          roundRectPath(ctx, boxX, boxY, boxW, boxH, 9);
          ctx.fill();

          ctx.strokeStyle = isWillow ? atmos.ldsTokens.accentPrimary : squadRim;
          ctx.lineWidth = 1.5;
          ctx.stroke();

          ctx.fillStyle = atmos.ldsTokens.bgSurface || 'rgba(11, 25, 22, 0.94)';
          ctx.beginPath();
          ctx.moveTo(cx - 5, boxY + boxH - 1);
          ctx.lineTo(cx + 5, boxY + boxH - 1);
          ctx.lineTo(cx, boxY + boxH + 6);
          ctx.closePath();
          ctx.fill();

          ctx.strokeStyle = isWillow ? atmos.ldsTokens.accentPrimary : squadRim;
          ctx.beginPath();
          ctx.moveTo(cx - 5, boxY + boxH);
          ctx.lineTo(cx, boxY + boxH + 6);
          ctx.lineTo(cx + 5, boxY + boxH);
          ctx.stroke();

          ctx.fillStyle = atmos.ldsTokens.textPrimary || '#f4ead5';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(text, cx, boxY + boxH / 2);
        }
      }

      ctx.restore();
    }

    // =========================================================================
    // 4. AMBIENT ECOLOGICAL PARTICLE & WEATHER LAYER (80-PARTICLE POOL)
    // =========================================================================

    const PARTICLE_POOL_SIZE = 80;
    const PARTICLE_POOL = Array.from({ length: PARTICLE_POOL_SIZE }, (_, idx) => {
      const h1 = hash2D(idx, 13, 7);
      const h2 = hash2D(idx, 29, 19);
      const h3 = hash2D(idx, 47, 31);
      const kinds = ['spore_mote', 'forge_spark', 'blossom_petal', 'ion_crystal'];
      return {
        index: idx,
        kind: kinds[idx % 4],
        baseX: 4 + h1 * 40,
        baseY: 4 + h2 * 40,
        phase: h3 * Math.PI * 2,
        speed: 0.35 + h1 * 0.55,
        size: 1.4 + h2 * 2.4
      };
    });

    /**
     * Updates and renders the self-managed pool of up to 80 ambient ecological particles.
     * Respects ZT-9 `reducedMotion` by freezing motion while preserving warm static ambiance.
     */
    function updateAndRenderAmbientParticles(
      ctx,
      world,
      camera,
      animTick = 0,
      options = {}
    ) {
      if (!ctx) return;
      const env = normalizeWorldContext(ctx, world, camera, animTick, options);
      const { scale, offsetX, offsetY, canvasW, canvasH, timeSec, atmos, biomeId } = env;

      ctx.save();

      for (let i = 0; i < PARTICLE_POOL_SIZE; i++) {
        const p = PARTICLE_POOL[i];
        let wx = p.baseX;
        let wy = p.baseY;
        let color = '#32f5c8';
        let alpha = 0.55;
        let radius = Math.max(1.4, (p.size * scale) / 26);

        if (p.kind === 'forge_spark') {
          const anchorX = biomeId === 'forge_caldera' ? p.baseX : 28 + (p.baseX % 14);
          const anchorY = biomeId === 'forge_caldera' ? p.baseY : 6 + (p.baseY % 12);
          const rise = (timeSec * p.speed * 1.4 + p.phase) % 3.5;
          wx = anchorX + Math.sin(timeSec * 1.8 + p.phase) * 0.6;
          wy = anchorY - rise;
          color = i % 2 === 0 ? '#ff9838' : '#fde047';
          alpha = clamp((1 - rise / 3.5) * 0.78, 0.1, 0.8);
        } else if (p.kind === 'blossom_petal') {
          const anchorX = 7 + (p.baseX % 16);
          const anchorY = 20 + (p.baseY % 15);
          const drift = (timeSec * p.speed * 0.7 + p.phase) % 4.0;
          wx = anchorX + Math.cos(timeSec * 1.1 + p.phase) * 0.9 + drift * 0.35;
          wy = anchorY + drift * 0.55;
          color = i % 2 === 0 ? '#fbcfe8' : '#a7f3d0';
          alpha = 0.62;
        } else if (p.kind === 'ion_crystal') {
          const driftX = Math.cos(timeSec * p.speed + p.phase) * 1.2;
          const driftY = Math.sin(timeSec * p.speed * 1.3 + p.phase) * 0.9;
          wx = p.baseX + driftX;
          wy = p.baseY + driftY;
          color = atmos.polarityInversion ? '#e879f9' : '#7dd3fc';
          alpha = env.kpExo >= 5.0 ? 0.68 : 0.32;
        } else {
          const wanderX = Math.sin(timeSec * p.speed + p.phase) * 1.4;
          const wanderY = Math.cos(timeSec * p.speed * 0.9 + p.phase) * 1.1;
          wx = p.baseX + wanderX;
          wy = p.baseY + wanderY;
          color = i % 3 === 0 ? '#fde047' : atmos.bioColor;
          const pulse = 0.55 + 0.45 * Math.sin(timeSec * 2.5 + p.phase);
          alpha = clamp(atmos.bioIntensity * 0.85 * pulse, 0.18, 0.88);
        }

        const sx = offsetX + wx * scale;
        const sy = offsetY + wy * scale;
        if (sx < -16 || sy < -16 || sx > canvasW + 16 || sy > canvasH + 16) continue;

        ctx.globalAlpha = alpha;
        if (p.kind === 'spore_mote' || p.kind === 'forge_spark') {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(sx, sy, radius * 2.1, 0, Math.PI * 2);
          ctx.globalAlpha = alpha * 0.28;
          ctx.fill();
          ctx.globalAlpha = alpha;
        }

        ctx.fillStyle = color;
        ctx.beginPath();
        if (p.kind === 'blossom_petal') {
          ctx.ellipse(sx, sy, radius * 1.3, radius * 0.75, p.phase + timeSec, 0, Math.PI * 2);
        } else {
          ctx.arc(sx, sy, radius, 0, Math.PI * 2);
        }
        ctx.fill();
      }

      ctx.restore();
    }

    /**
     * Screen-Space Post-Process Atmosphere, God-Rays, Aurora Curtains & Cozy Vignette.
     */
    function renderPostProcessAtmosphere(
      ctx,
      canvasWidth,
      canvasHeight,
      worldState,
      camera,
      options = {}
    ) {
      if (!ctx) return;
      const w = Number(canvasWidth || ctx.canvas?.width || 960);
      const h = Number(canvasHeight || ctx.canvas?.height || 640);
      const tick = options?.animTick ?? worldState?.animTick ?? 0;
      const env = normalizeWorldContext(ctx, worldState, camera, tick, {
        ...options,
        width: w,
        height: h
      });
      const { atmos, timeSec } = env;

      ctx.save();

      // 1. Subtle Dappled Cloud-Shadow Drift (Midday & Dawn)
      if (atmos.cloudShadowAlpha > 0.01) {
        ctx.fillStyle = `rgba(8, 22, 28, ${atmos.cloudShadowAlpha.toFixed(3)})`;
        for (let c = 0; c < 3; c++) {
          const drift = ((timeSec * 14 + c * (w * 0.42)) % (w * 1.4)) - w * 0.2;
          const cy = h * (0.25 + c * 0.28);
          ctx.beginPath();
          ctx.ellipse(drift, cy, w * 0.24, h * 0.09, -0.22, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // 2. Multi-Stop Twin-Sun & Triple-Moon Atmospheric Color-Grading Wash
      const skyGrad = ctx.createLinearGradient(0, 0, 0, h);
      skyGrad.addColorStop(0, atmos.skyGradient.top);
      skyGrad.addColorStop(0.52, atmos.skyGradient.mid);
      skyGrad.addColorStop(1, atmos.skyGradient.horizon);
      ctx.fillStyle = skyGrad;
      ctx.fillRect(0, 0, w, h);

      const mistGrad = ctx.createLinearGradient(0, h * 0.65, 0, h);
      mistGrad.addColorStop(0, 'rgba(0, 0, 0, 0)');
      mistGrad.addColorStop(1, atmos.groundMistColor);
      ctx.fillStyle = mistGrad;
      ctx.fillRect(0, h * 0.65, w, h * 0.35);

      // 3. Volumetric Twin-Sun / Triple-Moon God-Ray Light Shafts
      if (atmos.godRayAlpha > 0.05) {
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        const rayCount = 4;
        for (let r = 0; r < rayCount; r++) {
          const shimmer = 0.75 + 0.25 * Math.sin(timeSec * 0.9 + r * 1.7);
          const startX =
            atmos.dayPhase === 'DUSK_CRAFT' || atmos.dayPhase === 'THE_FEAST'
              ? w * (0.55 + r * 0.11)
              : w * (0.08 + r * 0.14);
          const endX = startX + Math.sin(atmos.godRayAngle) * h * 0.75;
          const rayW = w * (0.055 + (r % 2) * 0.025);

          const rayGrad = ctx.createLinearGradient(startX, 0, endX, h * 0.85);
          rayGrad.addColorStop(0, atmos.godRayColor);
          rayGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

          ctx.globalAlpha = atmos.godRayAlpha * shimmer;
          ctx.fillStyle = rayGrad;
          ctx.beginPath();
          ctx.moveTo(startX - rayW * 0.4, 0);
          ctx.lineTo(startX + rayW * 0.4, 0);
          ctx.lineTo(endX + rayW * 1.15, h * 0.88);
          ctx.lineTo(endX - rayW * 1.15, h * 0.88);
          ctx.closePath();
          ctx.fill();
        }
        ctx.restore();
      }

      // 4. Overhead Geomagnetic Aurora / Spore-Ribbon Curtains (kpExo >= 5.0)
      if (atmos.auroraActive && atmos.auroraIntensity > 0.05) {
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        const ribbonBands = 3;
        const pal = atmos.auroraPalette;
        const colors = [pal.primary, pal.secondary, pal.tertiary];

        for (let b = 0; b < ribbonBands; b++) {
          const baseY = h * (0.07 + b * 0.055);
          const ribbonH = h * (0.11 + b * 0.03);
          const aGrad = ctx.createLinearGradient(0, baseY, 0, baseY + ribbonH);
          aGrad.addColorStop(0, 'rgba(0, 0, 0, 0)');
          aGrad.addColorStop(0.35, colors[b % colors.length]);
          aGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

          ctx.globalAlpha = atmos.auroraIntensity * (0.32 - b * 0.06);
          ctx.fillStyle = aGrad;
          ctx.beginPath();
          ctx.moveTo(0, baseY + ribbonH);

          const steps = 16;
          for (let s = 0; s <= steps; s++) {
            const x = (s / steps) * w;
            const wave =
              Math.sin(s * 0.55 + timeSec * 1.3 + b * 1.4) * (h * 0.025) +
              Math.cos(s * 0.28 - timeSec * 0.8) * (h * 0.015);
            ctx.lineTo(x, baseY + wave);
          }
          ctx.lineTo(w, baseY + ribbonH);
          ctx.closePath();
          ctx.fill();
        }
        ctx.restore();
      }

      // 5. Soft Cinematic Vignette Frame
      if (atmos.vignetteAlpha > 0.02) {
        const cx = w * 0.5;
        const cy = h * 0.5;
        const innerR = Math.min(w, h) * 0.36;
        const outerR = Math.hypot(w, h) * 0.55;
        const vigGrad = ctx.createRadialGradient(cx, cy, innerR, cx, cy, outerR);
        vigGrad.addColorStop(0, 'rgba(0, 0, 0, 0)');
        vigGrad.addColorStop(1, atmos.vignetteColor);
        ctx.fillStyle = vigGrad;
        ctx.fillRect(0, 0, w, h);
      }

      ctx.restore();
    }

    // =========================================================================
    // 5. HIGH-LEVEL EASY-TO-CALL PUBLIC HOOKS
    // =========================================================================

    function renderWorldPass(ctx, world, camera, animTick = 0, options = {}) {
      if (!ctx) return;
      const layer = options?.layer || 'all';
      if (layer === 'all' || layer === 'ground') {
        renderFerrofluidCaustics(ctx, world, camera, animTick, options);
        renderTerrainMicroDetails(ctx, world, camera, animTick, options);
      }
      if (layer === 'all' || layer === 'buildings' || layer === 'entities') {
        renderBuildingArtisticPass(ctx, world, camera, animTick, options);
      }
      if (layer === 'all' || layer === 'entities') {
        renderCitizenArtisticPass(
          ctx,
          world?.citizens || options?.citizens,
          world,
          camera,
          animTick,
          options
        );
        const willow =
          options?.willow ||
          (Array.isArray(world?.citizens)
            ? world.citizens.find(c => (c.id || c.characterId) === 'enclave_07_willow')
            : null);
        renderWillowArtisticAura(ctx, willow, world, camera, animTick, options);
        updateAndRenderAmbientParticles(ctx, world, camera, animTick, options);
      }
    }

    function renderScreenPass(ctx, width, height, world, animTick = 0, options = {}) {
      if (!ctx) return;
      const cam = options?.camera || world?.camera || null;
      renderPostProcessAtmosphere(ctx, width, height, world, cam, {
        ...options,
        animTick
      });
    }

    return Object.freeze({
      version: '1.1.0',
      DAY_PHASES,
      LDS_W3C_THEME_PACKS,
      AEGIS_HEARTH_MOTIFS,
      MICRO_CLIMATE_REGIMES,
      computeAtmosphericState,
      renderTerrainMicroDetails,
      renderFerrofluidCaustics,
      renderBuildingArtisticPass,
      renderWillowArtisticAura,
      renderCitizenArtisticPass,
      updateAndRenderAmbientParticles,
      renderPostProcessAtmosphere,
      renderWorldPass,
      renderScreenPass
    });
  }
);
