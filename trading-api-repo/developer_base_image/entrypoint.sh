#!/bin/bash -e

echo "starting up.."
sleep 30 # timeout so nodes that constantly fail don't fill up the logs too much

# verify is-git flag
if [[ -z "${MERCOR_IS_GIT}" ]] ; then
  echo "is-git flag not passed, please do"
  exit 1
fi

## verify credentials
if [[ -z "${MERCOR_SDK_USERNAME}" ]] || [[ -z "${MERCOR_SDK_PASSWORD}" ]] ; then
  echo "credentials not properly passed"
  exit 1
fi
echo "found mercor credentials for ${MERCOR_SDK_USERNAME}"

echo "setting up working dir"
rm -rf ./pull  # cleanup in case it failed before
mkdir -p ./pull

# get code content in the right place
case "${MERCOR_IS_GIT}" in

  "1") # git version
    echo "recoginized this is a git algorithm"

    # check for variable
    if [[ -z "${MERCOR_GIT_LINK}" ]] ; then
        echo "no git link provided though.. :("
        exit 1
    fi

    # Here we clone the repo inside the container
    echo "cloning repository..."
    git clone $MERCOR_GIT_LINK ./pull || echo "failed cloning algorithm repository"
    ;;

  "0") # browser version
    echo "recoginized this is a browser algorithm"

    # check for variable
    if [[ -z "${MERCOR_CODE_CONTENT}" ]] ; then
        echo "no algorithm content provided though.. :("
        exit 1
    fi

    # build entrypoint file
    touch ./pull/main.py
    echo "${MERCOR_CODE_CONTENT}" > ./pull/main.py || echo "failed building algorithm file"
    ;;

  *)
    echo "unrecognized option for is-git: ${MERCOR_IS_GIT}"
    exit 1
    ;;
esac


# run code
cd pull
echo "All set to start running! :)"
python main.py --mercor-git-link ${MERCOR_GIT_LINK} --mercor-sdk-username ${MERCOR_SDK_USERNAME} --mercor-sdk-password ${MERCOR_SDK_PASSWORD} && echo "Process exited naturally! :)" || echo "algorithm failed"
exit 0
