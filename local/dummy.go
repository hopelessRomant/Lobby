package main

import (
	"fmt"
	"log"
	"os"

	"github.com/ethereum/go-ethereum/ethclient"
)

func main() {
	infuraURL := os.Getenv("ETH_INFURA")
	if infuraURL == "" {
		log.Fatal("ETH_INFURA environment variable not set")
	}

	client, err := ethclient.Dial(infuraURL)
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()

	fmt.Println("Connected to Ethereum node via Infura!")
}
