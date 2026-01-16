#!/bin/bash

# Comprehensive PIP bash completion test for RHEL
# Finds completion scripts from RPM, tests all pip binaries, and runs functional tests

PACKAGE="${PACKAGE:-python3-pip}"


# Step 1: Find bash completion scripts in python3-pip RPM package
echo "Step 1: Finding bash completion scripts in $PACKAGE RPM package..."

COMPLETION_FILE=$(rpm -ql $PACKAGE 2>/dev/null | grep -E "/usr/share/bash-completion/completions/" || true)

if [[ -z "$COMPLETION_FILE" ]]; then
    echo "✗ No bash completion files found in $PACKAGE package"
    exit 1
fi

# Check if there's exactly one completion file
COMPLETION_FILE_COUNT=$(echo "$COMPLETION_FILE" | wc -l)

if [[ $COMPLETION_FILE_COUNT -gt 1 ]]; then
    echo "✗ Multiple bash completion files found in $PACKAGE package:"
    echo "$COMPLETION_FILE" | sed 's/^/  - /'
    echo "Expected exactly one completion file, found $COMPLETION_FILE_COUNT"
    exit 1
fi


echo "✓ Found completion file from $PACKAGE package:"
echo "$COMPLETION_FILE" | sed 's/^/  - /'

# Step 2: Find all pip binaries
echo
echo "Step 2: Finding all pip binaries..."
PIP_BINARIES=()
PIP_FILES=$(rpm -ql $PACKAGE | grep /bin/p)
for pip_file in $PIP_FILES; do
    if [[ -x "$pip_file" ]]; then
        pip_cmd=$(basename "$pip_file")
        PIP_BINARIES+=("$pip_cmd")
        echo "✓ Found: $pip_cmd -> $pip_file"
    fi
done

if [[ ${#PIP_BINARIES[@]} -eq 0 ]]; then
    echo "✗ No pip binaries found"
    exit 1
fi

echo "Total pip binaries found: ${#PIP_BINARIES[@]}"

# Step 3: Source completion scripts and test each binary
echo
echo "Step 3: Testing completion for each pip binary..."

for AS_POSIX in 0 1; do
    if [[ $AS_POSIX -eq 1 ]]; then
        echo "Testing in POSIX mode"
        POSIX="--posix"
    else
        echo "Testing in non-POSIX mode"
        POSIX=""
    fi

    echo "Sourcing: $COMPLETION_FILE"
    if bash --norc $POSIX -c "source $COMPLETION_FILE" ; then
        echo "✓ Successfully sourced $COMPLETION_FILE"
    else
        echo "! Warning: Failed to source $COMPLETION_FILE"
        exit 1
    fi

    export AS_POSIX
    for pip_exec in "${PIP_BINARIES[@]}"; do
        echo "Running expect test with $COMPLETION_FILE and $pip_exec..."
        if ./test_pip_completion.exp "$COMPLETION_FILE" "$pip_exec"; then
            echo "✓ Functional test passed"
        else
            echo "✗ Functional test failed"
            exit 1
        fi
    done

done


echo "✓ All tests completed successfully!"
