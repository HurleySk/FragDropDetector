function populateDetectionConfig(config) {
    const primaryKeywords = config.primary_keywords || ['drop', 'dropped', 'release', 'available', 'launch'];
    const secondaryKeywords = config.secondary_keywords || ['limited', 'exclusive', 'sale', 'batch', 'decant'];
    const exclusionKeywords = config.exclusion_keywords || ['looking for', 'where to buy', 'wtb', 'wts', 'iso', 'recommendation', 'review'];
    const trustedAuthors = config.trusted_authors || ['ayybrahamlmaocoln', 'wide_parsley1799', 'montagneparfums', 'mpofficial'];

    document.getElementById('primary-keywords').value = primaryKeywords.join('\n');
    document.getElementById('secondary-keywords').value = secondaryKeywords.join('\n');
    document.getElementById('exclusion-keywords').value = exclusionKeywords.join('\n');
    document.getElementById('trusted-authors').value = trustedAuthors.join('\n');

    const threshold = config.confidence_threshold || 0.4;
    document.getElementById('confidence-threshold').value = threshold;
    document.getElementById('confidence-value').textContent = threshold;
}

async function handleDetectionConfigSubmit(e) {
    e.preventDefault();

    const primaryKeywords = document.getElementById('primary-keywords').value
        .split('\n')
        .map(k => k.trim())
        .filter(k => k);

    const secondaryKeywords = document.getElementById('secondary-keywords').value
        .split('\n')
        .map(k => k.trim())
        .filter(k => k);

    const exclusionKeywords = document.getElementById('exclusion-keywords').value
        .split('\n')
        .map(k => k.trim())
        .filter(k => k);

    const trustedAuthors = document.getElementById('trusted-authors').value
        .split('\n')
        .map(a => a.trim())
        .filter(a => a);

    const config = {
        primary_keywords: primaryKeywords,
        secondary_keywords: secondaryKeywords,
        confidence_threshold: parseFloat(document.getElementById('confidence-threshold').value),
        known_vendors: ['montagneparfums', 'montagne_parfums'],
        exclusion_keywords: exclusionKeywords,
        trusted_authors: trustedAuthors
    };

    if (primaryKeywords.length === 0) {
        showAlert('Please add at least one primary keyword', 'error');
        return;
    }

    try {
        setLoading('detection-form', true);
        await saveDetectionConfig(config);
        const refreshedConfig = await loadConfig(true);
        if (refreshedConfig) {
            populateDetectionConfig(refreshedConfig.detection || {});
        }
    } catch (error) {
        // Error already shown
    } finally {
        setLoading('detection-form', false);
    }
}
