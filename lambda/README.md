Notes:

Creating a lambda function:

First create a project director for the given lambda function. This can be done using sam init:

`sam init --runtime python2.7 --output-dir /Users/grant.seward/GitHub/aws_streams/lambda --name sampleLambda`

If needed, information on sam can be found here: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html

Use Docker to create the Linux specific library bindings for additional packages:

Examples come from:
  https://medium.freecodecamp.org/escaping-lambda-function-hell-using-docker-40b187ec1e48

  `docker run -v <directory with your code>:/working -it --rm ubuntu`

  or for the current directory:

  `docker run -v $PWD:/working -it --rm ubuntu`

  The -vflag makes your code directory available inside the container in a directory called “working”.
  The -itflag means you get to interact with this container.
  The --rm flag means Docker will remove the container when you’re finished.

  `apt-get update
  apt-get install python3-pip -y
  pip3 install virtualenv
  `

  `cd working`
  (change to the current Mac working directory)

  Install the virtualenv as "venv"

  `virtualenv venv
  source venv/bin/activate
  `

  Activate the virtual environment and install the requirements

  `pip install -t ./build -r requirements.txt --upgrade`

  or

  `pip install -t ./build <library>`

  Install the zip package:

  `apt-get install zip -y`

  Zip everything up for the deployment

  `zip -r fileName.zip ./build`
